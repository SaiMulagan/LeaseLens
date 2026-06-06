"""In-memory document store.

A dict keyed by document id is plenty for a single-node demo and keeps the
project runnable with zero infrastructure. The interface (add / get / list /
review) is deliberately the shape you'd back with Postgres in production, so
swapping the implementation later touches nothing else.
"""

from __future__ import annotations

import hashlib
import threading
from uuid import UUID

from .pipeline import run_pipeline
from .schemas import Document, ReviewState


class DocumentStore:
    def __init__(self) -> None:
        self._docs: dict[UUID, Document] = {}
        self._by_hash: dict[str, UUID] = {}
        self._pdf: dict[UUID, bytes] = {}  # original PDF bytes, for the viewer
        self._lock = threading.Lock()

    def ingest(self, filename: str, pdf_bytes: bytes) -> Document:
        """Run the pipeline on a PDF and store the result. De-dupes by hash."""
        sha = hashlib.sha256(pdf_bytes).hexdigest()
        with self._lock:
            if sha in self._by_hash:  # duplicate upload collapses to one record
                return self._docs[self._by_hash[sha]]
        result = run_pipeline(pdf_bytes)
        doc = Document(filename=filename, sha256=sha, result=result)
        with self._lock:
            self._docs[doc.id] = doc
            self._by_hash[sha] = doc.id
            self._pdf[doc.id] = pdf_bytes
        return doc

    def get(self, doc_id: UUID) -> Document | None:
        return self._docs.get(doc_id)

    def get_pdf(self, doc_id: UUID) -> bytes | None:
        return self._pdf.get(doc_id)

    def list(self) -> list[Document]:
        return sorted(self._docs.values(), key=lambda d: d.uploaded_at, reverse=True)

    def review(
        self,
        doc_id: UUID,
        state: ReviewState,
        note: str | None = None,
        overrides: dict[str, str] | None = None,
    ) -> Document | None:
        doc = self._docs.get(doc_id)
        if not doc:
            return None
        doc.review_state = state
        doc.reviewer_note = note
        if overrides:
            doc.field_overrides.update(overrides)
        return doc

    def stats(self) -> dict:
        docs = list(self._docs.values())
        by_verdict = {"clean": 0, "minor": 0, "major": 0, "rejected": 0}
        by_state = {"needs_review": 0, "confirmed": 0, "overridden": 0}
        for d in docs:
            by_verdict[d.result.verdict] += 1
            by_state[d.review_state] += 1
        return {"total": len(docs), "by_verdict": by_verdict, "by_state": by_state}


STORE = DocumentStore()
