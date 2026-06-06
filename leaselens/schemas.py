"""Shared data contract for the LeaseLens pipeline, API, and UI.

The whole system speaks in these types. Stages take and return them, the
store persists them, and the API serialises them straight to the browser.
Keeping one contract is what lets the pipeline stay unit-testable and the
eval/seed paths reuse the exact code that serves live uploads.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

DocType = Literal["residential_lease", "rental_application", "coi", "unknown"]
Severity = Literal["minor", "major"]
Verdict = Literal["clean", "minor", "major", "rejected"]
Source = Literal["rule", "llm"]
ReviewState = Literal["needs_review", "confirmed", "overridden"]

# Issue taxonomy. Every flag the system can raise has a stable kind so the UI,
# the metrics, and any downstream learning loop can group them.
IssueKind = Literal[
    "missing_field",
    "deposit_exceeds_legal_max",
    "date_inversion",
    "term_length_mismatch",
    "missing_signature",
    "late_fee_excessive",
    "rent_out_of_market_band",
    "risky_clause",
    "unreadable_document",
    "wrong_document_type",
]


# ---------------------------------------------------------------------------
# Core records
# ---------------------------------------------------------------------------


class Issue(BaseModel):
    """One thing a human should look at. Rules and the LLM both emit these."""

    model_config = ConfigDict(extra="forbid")

    kind: IssueKind
    severity: Severity
    field: str
    value: str | None = None
    message: str
    source: Source
    confidence: float | None = None


class LeaseFields(BaseModel):
    """The structured shape we pull out of an unstructured lease PDF."""

    model_config = ConfigDict(extra="forbid")

    tenant_name: str | None = None
    landlord_name: str | None = None
    property_address: str | None = None
    unit: str | None = None
    city: str | None = None
    bedrooms: int | None = None
    monthly_rent: float | None = None
    security_deposit: float | None = None
    lease_start: str | None = None  # ISO date string
    lease_end: str | None = None
    term_months: int | None = None
    late_fee: float | None = None
    pets_allowed: bool | None = None
    tenant_signed: bool | None = None
    landlord_signed: bool | None = None

    # Per-field extraction confidence (0-1), keyed by field name. Lets the UI
    # highlight values the extractor was unsure about.
    confidence: dict[str, float] = Field(default_factory=dict)


class PipelineResult(BaseModel):
    """Everything the pipeline knows about one document after a full run."""

    model_config = ConfigDict(extra="forbid")

    doc_type: DocType
    doc_type_confidence: float
    verdict: Verdict
    fields: LeaseFields
    issues: list[Issue]
    extraction_profile: str
    ocr_pages: int = 0  # number of pages whose text was recovered via OCR
    latency_ms: int


class Document(BaseModel):
    """A stored document: the pipeline result plus review metadata."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    filename: str
    sha256: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    result: PipelineResult
    review_state: ReviewState = "needs_review"
    reviewer_note: str | None = None
    field_overrides: dict[str, str] = Field(default_factory=dict)
