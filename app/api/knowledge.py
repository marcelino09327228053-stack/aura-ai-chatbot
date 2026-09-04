"""Knowledge document ingestion, listing, search, and deletion."""

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.core.deps import require_auth
from app.database import knowledge_repository
from app.services.document_extractor import ExtractionError, extract_text

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _chunk_text(text: str, size: int = 1200, overlap: int = 150) -> list[str]:
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start + size // 2:
                end = boundary
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [chunk for chunk in chunks if chunk]


@router.post("/documents", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    ctx=Depends(require_auth),
):
    name = Path(file.filename or "document.txt").name
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Document exceeds the 2 MB limit.")
    try:
        text, extraction_method = extract_text(name, raw)
    except ExtractionError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    chunks = _chunk_text(text)
    if not chunks:
        raise HTTPException(status_code=422, detail="Document contains no searchable text.")
    document = knowledge_repository.create_document(
        ctx.company_id, name, file.content_type or "text/plain", len(raw), chunks
    )
    document["extraction_method"] = extraction_method
    return document


@router.get("/documents")
def list_documents(ctx=Depends(require_auth)):
    return knowledge_repository.list_documents(ctx.company_id)


@router.delete("/documents/{document_id}")
def delete_document(document_id: int, ctx=Depends(require_auth)):
    if not knowledge_repository.delete_document(ctx.company_id, document_id):
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"deleted": True}


@router.get("/search")
def search_knowledge(
    q: str = Query(min_length=2, max_length=500),
    ctx=Depends(require_auth),
):
    return knowledge_repository.search(ctx.company_id, q)
