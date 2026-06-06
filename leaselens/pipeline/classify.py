"""Stage 1 - document classification.

Bounce anything that is not the document we built the pipeline for *before* a
reviewer ever wastes time on it. A lease, a rental application, and a
certificate of insurance all flow through a property manager's inbox; only the
lease should continue down this pipeline. The classifier is a transparent
keyword-score model: easy to read, easy to defend, and trivial to swap for a
trained model behind the same signature.
"""

from __future__ import annotations

from ..schemas import DocType

# Signals per class. Weighted so a couple of strong hits beats incidental ones.
_SIGNALS: dict[DocType, dict[str, float]] = {
    "residential_lease": {
        "residential lease": 3.0,
        "lease agreement": 3.0,
        "landlord": 1.0,
        "tenant": 1.0,
        "monthly rent": 1.5,
        "security deposit": 1.5,
        "term of tenancy": 1.0,
        "premises": 0.7,
    },
    "rental_application": {
        "rental application": 3.0,
        "applicant": 1.5,
        "employer": 1.0,
        "annual income": 1.0,
        "previous address": 1.0,
        "authorize a credit": 1.5,
    },
    "coi": {
        "certificate of insurance": 3.0,
        "acord": 2.0,
        "policy number": 1.5,
        "general liability": 1.5,
        "insurer": 1.0,
    },
}


def classify(text: str) -> tuple[DocType, float]:
    """Return (doc_type, confidence in 0-1)."""
    lowered = text.lower()
    scores: dict[DocType, float] = {}
    for doc_type, signals in _SIGNALS.items():
        scores[doc_type] = sum(w for kw, w in signals.items() if kw in lowered)

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0 or total == 0:
        return "unknown", 0.0
    confidence = round(scores[best] / total, 3)
    # A single weak hit shouldn't read as a confident classification.
    if scores[best] < 3.0:
        return ("unknown", confidence) if confidence < 0.5 else (best, confidence)
    return best, confidence
