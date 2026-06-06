"""Stage 3 - field extraction from unstructured lease text.

This is the heart of the "unstructured document" problem. A lease is prose, not
a form, so we cannot just read AcroForm widgets - we have to *find* the values
in free text. Two interchangeable profiles do that:

* ``heuristic`` (default): labelled-pattern + regex extraction. Deterministic,
  offline, fast, and good enough to demo end-to-end with no API key.
* ``llm``: hands the text to an LLM with a strict JSON schema. Enabled when
  ``OPENAI_API_KEY`` is set and the ``openai`` package is installed.

Both return the same ``LeaseFields`` contract, with a per-field confidence map,
so everything downstream is identical regardless of how the value was found.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime

from ..schemas import LeaseFields

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Small parsing helpers
# ---------------------------------------------------------------------------

_MONEY_RE = r"\$?\s*([0-9][0-9,]*(?:\.[0-9]{2})?)"


def _money(s: str | None) -> float | None:
    if not s:
        return None
    m = re.search(_MONEY_RE, s)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


_DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y", "%m/%d/%y")


def _date(s: str | None) -> str | None:
    """Normalise any recognised date spelling to an ISO date string."""
    if not s:
        return None
    s = s.strip().strip(".")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _first(text: str, pattern: str, flags=re.I) -> str | None:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


# ---------------------------------------------------------------------------
# Heuristic profile
# ---------------------------------------------------------------------------


def _extract_heuristic(text: str) -> LeaseFields:
    f = LeaseFields()
    conf: dict[str, float] = {}

    def set_field(name: str, value, c: float):
        if value is not None and value != "":
            setattr(f, name, value)
            conf[name] = c

    # A proper name: 2-4 capitalised tokens on one line. The label is matched
    # case-insensitively with a scoped flag, but the name itself stays
    # case-sensitive so we don't grab lowercase clause text like "should pay".
    NAME = r"([A-Z][a-zA-Z.'\-]+(?:[ \t]+[A-Z][a-zA-Z.'\-]+){1,3})"
    STOP = {
        "date", "name", "no", "none", "phone", "social", "drivers", "tenant",
        "landlord", "lessee", "lessor", "rent", "security", "signature",
        "premises", "address", "property", "page", "the", "this",
    }

    def find_name(*labels: str) -> str | None:
        for label in labels:
            for m in re.finditer(rf"(?i:{label})\s*[:#\-]?\s*{NAME}", text):
                cand = m.group(1).strip()
                if cand.split()[0].lower() not in STOP:
                    return cand
        return None

    def find(*patterns: str) -> str | None:
        for pat in patterns:
            m = re.search(pat, text, re.I)
            if m:
                return m.group(1).strip()
        return None

    set_field("tenant_name", find_name("tenant name", "tenant", "lessee", "resident"), 0.85)
    set_field("landlord_name", find_name("landlord name", "landlord", "lessor", "owner"), 0.85)

    set_field("property_address", find(
        r"(?m)^\s*Premises:\s*([^,\n]+)",
        r"(?:property address|premises|located at|address)\s*:?\s*(\d+[^,\n]+)",
    ), 0.8)
    set_field("unit", find(r"(?:unit|apt|apartment|suite|room)\s*#?\s*([A-Za-z0-9\-]{1,5})\b"), 0.75)
    set_field("city", find(r"(?:,\s*)([A-Za-z .]+),\s*[A-Z]{2}\s*\d{5}"), 0.7)

    bedrooms = find(r"bedrooms?\s*:?\s*(\d+)", r"(\d+)[ \t]*(?:bed|bedroom)s?\b")
    set_field("bedrooms", int(bedrooms) if bedrooms else None, 0.75)

    set_field("monthly_rent", _money(find(
        r"monthly rent\s*:?\s*(\$?[\d,]+(?:\.\d{2})?)",
        r"rent[^$\n]{0,40}(\$[\d,]+(?:\.\d{2})?)\s*(?:per month|/\s*month|a month|monthly)",
        r"(\$[\d,]+(?:\.\d{2})?)\s*(?:per month|/\s*month|a month|monthly)",
        r"rent\s*:?\s*(\$[\d,]+(?:\.\d{2})?)",
    )), 0.88)
    set_field("security_deposit", _money(find(
        r"security deposit\s*:?\s*(?:of\s*)?(\$?[\d,]+(?:\.\d{2})?)",
        r"deposit[^$\n]{0,25}(\$[\d,]+(?:\.\d{2})?)",
    )), 0.88)
    set_field("late_fee", _money(find(r"late fee\s*:?\s*(\$?[\d,]+(?:\.\d{2})?)")), 0.8)

    set_field("lease_start", _date(find(
        r"beginning\s+([A-Za-z0-9,/\- ]+?)\s+and ending",
        r"(?:commenc\w+|start\w*|begin\w*|since|effective)[^0-9\n]{0,12}(\d{1,2}/\d{1,2}/\d{2,4})",
        r"(?:commenc\w+|start\w*|begin\w*|effective)[^0-9\n]{0,12}(\d{4}-\d{2}-\d{2})",
    )), 0.85)
    set_field("lease_end", _date(find(
        r"ending\s+([A-Za-z0-9,/\- ]+?)(?:\.|\n|$)",
        r"(?:end\w*|through|until|expir\w+|terminat\w+)[^0-9\n]{0,12}(\d{1,2}/\d{1,2}/\d{2,4})",
    )), 0.85)
    term = find(r"lease term\s*:?\s*(\d+)\s*month", r"(?:at least|for|term of)\s+(\d+)\s*month")
    set_field("term_months", int(term) if term else None, 0.8)

    pets = find(r"pets?\s*:?\s*(allowed|not allowed|permitted|prohibited)")
    if pets is None and re.search(r"no pets", text, re.I):
        pets = "prohibited"
    if pets:
        set_field("pets_allowed", pets.lower() in ("allowed", "permitted"), 0.75)

    # Signatures: True if a name follows the label, False if the label exists but
    # is blank (only a date / underscores), None if there's no signature line.
    def signed(*labels: str) -> bool | None:
        for label in labels:
            m = re.search(rf"(?i:{label})\s*[:#\-]?\s*(.*)", text)
            if m:
                return bool(re.match(rf"\s*{NAME}", m.group(1)))
        return None

    ts = signed(r"tenant signature", r"signature of tenant", r"tenant'?s signature")
    if ts is not None:
        set_field("tenant_signed", ts, 0.7)
    ls = signed(r"landlord signature", r"signature of landlord", r"landlord'?s signature")
    if ls is not None:
        set_field("landlord_signed", ls, 0.7)

    f.confidence = conf
    return f


# ---------------------------------------------------------------------------
# LLM profile (optional)
# ---------------------------------------------------------------------------

_LLM_SYSTEM = (
    "You extract structured fields from a US residential lease. Return ONLY "
    "JSON with keys: tenant_name, landlord_name, property_address, unit, city, "
    "bedrooms, monthly_rent, security_deposit, lease_start (YYYY-MM-DD), "
    "lease_end (YYYY-MM-DD), term_months, late_fee, pets_allowed, "
    "tenant_signed, landlord_signed. Use null for anything not present."
)


def _extract_llm(text: str) -> LeaseFields:
    from openai import OpenAI  # imported lazily so it stays optional

    client = OpenAI()
    resp = client.chat.completions.create(
        model=os.getenv("LEASELENS_LLM_MODEL", "gpt-4o-mini"),
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _LLM_SYSTEM},
            {"role": "user", "content": text[:12000]},
        ],
        temperature=0,
    )
    data = json.loads(resp.choices[0].message.content)
    data = {k: v for k, v in data.items() if k in LeaseFields.model_fields}
    fields = LeaseFields(**data)
    # The model returned every field, so mark uniform high confidence.
    fields.confidence = {k: 0.95 for k, v in data.items() if v is not None}
    return fields


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def active_profile() -> str:
    if os.getenv("OPENAI_API_KEY"):
        try:
            import openai  # noqa: F401

            return "llm"
        except ImportError:
            pass
    return "heuristic"


def extract_fields(text: str, profile: str | None = None) -> tuple[LeaseFields, str]:
    profile = profile or active_profile()
    if profile == "llm":
        try:
            return _extract_llm(text), "llm"
        except Exception as exc:  # noqa: BLE001 - never fail the pipeline on LLM
            log.warning("LLM extraction failed (%s); falling back to heuristic", exc)
    return _extract_heuristic(text), "heuristic"
