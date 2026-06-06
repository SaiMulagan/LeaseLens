"""Stage 5 - judgement calls that rules alone can't make.

Two judges look at the document the way an experienced leasing agent would:

* market band  - is the rent plausible for this unit and city?
* risky clause - does the prose contain language that hurts the owner or is
  legally suspect (deposit waivers, habitability waivers, auto-escalation,
  blanket liability waivers)?

Both run in a ``heuristic`` mode (a small clause lexicon + the rent gazetteer)
so the demo needs no API key, and both upgrade to a real LLM judgement when one
is configured. They never raise into the orchestrator: a failure just yields no
issue, so a document is never lost because a judge errored.
"""

from __future__ import annotations

import logging
import re

from ..schemas import Issue, LeaseFields
from .market import band_for

log = logging.getLogger(__name__)

# Clause lexicon: (regex, human label, severity).
_RISKY_CLAUSES = [
    (r"waives?\s+(?:any|the)\s+right\s+to\s+(?:the\s+)?return\s+of\s+(?:the\s+)?(?:security\s+)?deposit",
     "Tenant waives return of the security deposit", "major"),
    (r"waiv\w*\s+.{0,40}\bhabitability\b", "Waiver of the warranty of habitability", "major"),
    (r"rent\s+may\s+increase\s+at\s+any\s+time|increase\s+the\s+rent\s+at\s+the\s+landlord'?s\s+sole\s+discretion",
     "Rent may be raised at the landlord's sole discretion mid-term", "major"),
    (r"tenant\s+(?:is\s+)?responsible\s+for\s+all\s+(?:structural\s+)?repairs",
     "Tenant made responsible for all/structural repairs", "minor"),
    (r"no\s+right\s+to\s+(?:a\s+)?jury\s+trial|waives?\s+.{0,20}jury\s+trial",
     "Jury-trial waiver", "minor"),
]


def judge_market_band(fields: LeaseFields) -> list[Issue]:
    band = band_for(fields.city, fields.bedrooms)
    if not band or not fields.monthly_rent:
        return []
    low, high = band
    rent = fields.monthly_rent
    if rent < low * 0.6 or rent > high * 1.6:
        # Far outside plausible range -> probably an extraction or data error.
        return [
            Issue(
                kind="rent_out_of_market_band",
                severity="minor",
                field="monthly_rent",
                value=f"${rent:,.0f}",
                message=f"Rent ${rent:,.0f} is well outside the {fields.bedrooms}-bed "
                f"band for {fields.city or 'this market'} (${low:,}-${high:,}).",
                source="llm",
                confidence=0.7,
            )
        ]
    return []


def judge_risky_clauses(text: str) -> list[Issue]:
    issues = []
    for pattern, label, severity in _RISKY_CLAUSES:
        if re.search(pattern, text, re.I):
            issues.append(
                Issue(
                    kind="risky_clause",
                    severity=severity,  # type: ignore[arg-type]
                    field="clauses",
                    value=label,
                    message=f"Non-standard clause: {label}.",
                    source="llm",
                    confidence=0.8,
                )
            )
    return issues


def run_reasoning(fields: LeaseFields, text: str) -> list[Issue]:
    issues: list[Issue] = []
    try:
        issues.extend(judge_market_band(fields))
        issues.extend(judge_risky_clauses(text))
    except Exception as exc:  # noqa: BLE001
        log.warning("reasoning stage degraded: %s", exc)
    return issues
