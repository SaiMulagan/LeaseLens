"""FastAPI app: upload endpoint, review endpoints, and the reviewer UI.

The HTTP layer is thin on purpose - it validates input, calls the store (which
calls the pipeline), and serialises the shared schema straight to JSON. All the
intelligence lives in ``pipeline/``.
"""

from __future__ import annotations

import os
from uuid import UUID

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel

from .pipeline.extract import active_profile
from .store import STORE

app = FastAPI(title="LeaseLens", version="0.1.0")

WEB_DIR = os.path.join(os.path.dirname(__file__), "web")
SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "samples")


@app.get("/")
def index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))


@app.get("/api/profile")
def profile():
    return {"extraction_profile": active_profile()}


@app.get("/api/stats")
def stats():
    return STORE.stats()


@app.get("/api/documents")
def list_documents():
    out = []
    for d in STORE.list():
        f = d.result.fields
        out.append(
            {
                "id": str(d.id),
                "filename": d.filename,
                "uploaded_at": d.uploaded_at.isoformat(),
                "doc_type": d.result.doc_type,
                "verdict": d.result.verdict,
                "review_state": d.review_state,
                "issue_count": len(d.result.issues),
                "tenant_name": f.tenant_name,
                "property_address": f.property_address,
                "monthly_rent": f.monthly_rent,
                "extraction_profile": d.result.extraction_profile,
                "ocr_pages": d.result.ocr_pages,
                "latency_ms": d.result.latency_ms,
            }
        )
    return out


@app.get("/api/documents/{doc_id}")
def get_document(doc_id: UUID):
    doc = STORE.get(doc_id)
    if not doc:
        raise HTTPException(404, "document not found")
    return doc.model_dump(mode="json")


@app.get("/api/documents/{doc_id}/pdf")
def get_document_pdf(doc_id: UUID):
    """Serve the original uploaded PDF so the reviewer can open the source."""
    doc = STORE.get(doc_id)
    data = STORE.get_pdf(doc_id)
    if not doc or data is None:
        raise HTTPException(404, "pdf not found")
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{doc.filename}"'},
    )


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(400, "empty file")
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "only .pdf is accepted")
    doc = STORE.ingest(file.filename, data)
    return doc.model_dump(mode="json")


class ReviewBody(BaseModel):
    action: str  # "confirm" | "override"
    note: str | None = None
    overrides: dict[str, str] | None = None


@app.post("/api/documents/{doc_id}/review")
def review(doc_id: UUID, body: ReviewBody):
    if body.action not in ("confirm", "override"):
        raise HTTPException(400, "action must be 'confirm' or 'override'")
    state = "confirmed" if body.action == "confirm" else "overridden"
    doc = STORE.review(doc_id, state, body.note, body.overrides)
    if not doc:
        raise HTTPException(404, "document not found")
    return doc.model_dump(mode="json")


@app.get("/samples")
def list_samples():
    if not os.path.isdir(SAMPLES_DIR):
        return []
    return sorted(f for f in os.listdir(SAMPLES_DIR) if f.endswith(".pdf"))


@app.get("/samples/{name}")
def get_sample(name: str):
    path = os.path.join(SAMPLES_DIR, os.path.basename(name))
    if not os.path.isfile(path):
        raise HTTPException(404, "sample not found")
    return FileResponse(path, media_type="application/pdf")


def seed_from_samples() -> int:
    """Preload every sample PDF so the inbox is populated for a demo."""
    if not os.path.isdir(SAMPLES_DIR):
        return 0
    n = 0
    for name in sorted(os.listdir(SAMPLES_DIR)):
        if name.endswith(".pdf"):
            with open(os.path.join(SAMPLES_DIR, name), "rb") as fh:
                STORE.ingest(name, fh.read())
            n += 1
    return n
