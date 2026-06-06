"""End-to-end orchestration: text -> classify -> gate -> extract -> validate
-> reason -> verdict. One callable so the API, the seed script, and any future
eval harness all run the exact same path.
"""

from __future__ import annotations

import time

from ..schemas import Issue, LeaseFields, PipelineResult, Verdict
from .classify import classify
from .extract import extract_fields
from .gatecheck import gate_check
from .reason import run_reasoning
from .textract import extract_text
from .validate import run_rules


def _rollup(issues: list[Issue], rejected: bool) -> Verdict:
    if rejected:
        return "rejected"
    if any(i.severity == "major" for i in issues):
        return "major"
    if any(i.severity == "minor" for i in issues):
        return "minor"
    return "clean"


def run_pipeline(pdf_bytes: bytes, profile: str | None = None) -> PipelineResult:
    start = time.monotonic()

    text_result = extract_text(pdf_bytes)
    doc_type, dt_conf = classify(text_result.text)

    gate_issues = gate_check(text_result)

    # Hard stops: wrong document, or unreadable. Don't pretend to extract.
    if doc_type != "residential_lease":
        gate_issues.append(
            Issue(
                kind="wrong_document_type",
                severity="major",
                field="document",
                value=doc_type,
                message=f"Classified as '{doc_type}', not a residential lease; "
                "bounced before extraction.",
                source="rule",
            )
        )
    rejected = doc_type != "residential_lease" or any(
        i.kind == "unreadable_document" for i in gate_issues
    )

    if rejected:
        return PipelineResult(
            doc_type=doc_type,
            doc_type_confidence=dt_conf,
            verdict=_rollup(gate_issues, rejected=True),
            fields=LeaseFields(),
            issues=gate_issues,
            extraction_profile="none",
            ocr_pages=text_result.ocr_pages,
            latency_ms=round((time.monotonic() - start) * 1000),
        )

    fields, used_profile = extract_fields(text_result.text, profile)
    issues = gate_issues + run_rules(fields) + run_reasoning(fields, text_result.text)

    return PipelineResult(
        doc_type=doc_type,
        doc_type_confidence=dt_conf,
        verdict=_rollup(issues, rejected=False),
        fields=fields,
        issues=issues,
        extraction_profile=used_profile,
        ocr_pages=text_result.ocr_pages,
        latency_ms=round((time.monotonic() - start) * 1000),
    )
