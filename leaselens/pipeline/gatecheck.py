"""Stage 2 - gate checks.

Cheap structural guards that run before any expensive extraction so broken or
hostile inputs fail fast with a clear reason instead of corrupting the inbox.
"""

from __future__ import annotations

from ..schemas import Issue
from .textract import PdfTextResult

MAX_PAGES = 60
MIN_TEXT_CHARS = 200  # a real lease has at least this much text


def gate_check(text_result: PdfTextResult) -> list[Issue]:
    issues: list[Issue] = []

    if text_result.page_count > MAX_PAGES:
        issues.append(
            Issue(
                kind="unreadable_document",
                severity="major",
                field="document",
                value=f"{text_result.page_count} pages",
                message=f"Document has {text_result.page_count} pages "
                f"(max {MAX_PAGES}); likely a misfiled batch scan.",
                source="rule",
            )
        )

    # If OCR already recovered enough text, the document is readable and flows
    # on normally. We only flag when there still isn't enough text to work with.
    if len(text_result.text.strip()) < MIN_TEXT_CHARS:
        detail = (
            "scanned image and OCR recovered no readable text"
            if text_result.scanned_pages > 0
            else "almost no extractable text"
        )
        issues.append(
            Issue(
                kind="unreadable_document",
                severity="major",
                field="document",
                value=detail,
                message=f"Could not read the document: {detail}.",
                source="rule",
            )
        )

    return issues
