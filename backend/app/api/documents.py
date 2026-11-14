import os
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.database.models import Document
from backend.app.services.rag.ingestion import ingest_pdf_document
from backend.app.services.rag.retrieval import faiss_retriever
from backend.app.services.rag.corpus.sources import CorpusSourcesError, load_corpus_sources
from backend.app.core.config import settings
from backend.app.core.security import validate_document_file, sanitize_filename
from backend.app.core.logging import logger

router = APIRouter(prefix="/api/documents", tags=["Document Knowledge Base"])

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(None),
    issuing_authority: str = Form("महाराष्ट्र शासन / Govt of Maharashtra"),
    publication_date: str = Form(None),
    source_url: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    Uploads and indexes an official government scheme PDF document into the FAISS vector knowledge base.
    Supports scanned PDFs via transparent Tesseract OCR fallback.
    """
    validate_document_file(file)
    safe_name = sanitize_filename(file.filename or "government_scheme.pdf")
    destination_path = settings.DOCUMENTS_DIR / safe_name

    # Save PDF file to documents directory
    with open(destination_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    doc_title = title.strip() if (title and title.strip()) else safe_name

    try:
        ingestion_result = ingest_pdf_document(
            file_path=str(destination_path),
            title=doc_title,
            db=db,
            source_url=source_url or "",
            issuing_authority=issuing_authority,
            publication_date=publication_date or ""
        )
        return {
            "status": "success",
            "message": f"Document '{doc_title}' indexed successfully.",
            "data": ingestion_result
        }
    except Exception as e:
        logger.error(f"Error during document ingestion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process and index document: {str(e)}"
        )

@router.get("")
async def list_documents(db: Session = Depends(get_db)):
    """Lists all uploaded documents with processing status and chunk statistics."""
    docs = db.query(Document).order_by(Document.upload_date.desc()).all()
    index_stats = faiss_retriever.get_stats()

    return {
        "total_documents": len(docs),
        "index_stats": index_stats,
        "documents": [
            {
                "id": d.id,
                "title": d.title,
                "filename": d.filename,
                "issuing_authority": d.issuing_authority,
                "publication_date": d.publication_date,
                "upload_date": d.upload_date.isoformat() if d.upload_date else None,
                "processing_status": d.processing_status,
                "chunk_count": d.chunk_count,
                "file_size_kb": d.file_size_kb,
                "error_message": d.error_message
            } for d in docs
        ]
    }

@router.get("/sources")
def list_corpus_sources():  # sync: reads a small file, so FastAPI runs it in its threadpool
    """Lists the official documents the knowledge base is built from (public fields only)."""
    try:
        sources = load_corpus_sources(settings.DOCUMENTS_DIR / "manifest.json")
    except CorpusSourcesError as exc:
        logger.error(f"Corpus sources unavailable: {exc}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="The document list is not available right now.")
    return {"total": len(sources), "documents": [s.model_dump() for s in sources]}


@router.delete("/{document_id}")
async def delete_document(document_id: str, db: Session = Depends(get_db)):
    """Deletes a document and purges its indexed vectors from the FAISS database."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Remove from FAISS index
    removed_chunks = faiss_retriever.delete_document(document_id)

    # Remove PDF file if exists
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception as e:
            logger.warning(f"Could not delete physical file {doc.file_path}: {e}")

    db.delete(doc)
    db.commit()

    return {
        "status": "success",
        "message": f"Document '{doc.title}' deleted successfully.",
        "removed_chunks": removed_chunks
    }

@router.post("/reindex")
async def reindex_all_documents(db: Session = Depends(get_db)):
    """Rebuilds the entire FAISS vector index from stored PDF files."""
    docs = db.query(Document).filter(Document.processing_status == "indexed").all()
    if not docs:
        faiss_retriever.delete_document("all")
        return {"status": "success", "message": "No indexed documents found to rebuild.", "reindexed_documents": 0}

    # Reset FAISS
    faiss_retriever._init_new_index()
    total_reindexed = 0

    for d in docs:
        if d.file_path and os.path.exists(d.file_path):
            try:
                ingest_pdf_document(
                    file_path=d.file_path,
                    title=d.title,
                    db=db,
                    doc_id=d.id,
                    source_url=d.source_url,
                    issuing_authority=d.issuing_authority,
                    publication_date=d.publication_date
                )
                total_reindexed += 1
            except Exception as e:
                logger.error(f"Reindexing failed for {d.title}: {e}")

    return {
        "status": "success",
        "message": f"Successfully reindexed {total_reindexed} documents.",
        "stats": faiss_retriever.get_stats()
    }

