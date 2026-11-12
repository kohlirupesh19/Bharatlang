import os
from pathlib import Path
from typing import Dict, Any
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.utils.pdf import extract_text_from_pdf
from backend.app.services.rag.chunking import chunk_document_pages
from backend.app.services.rag.retrieval import faiss_retriever
from backend.app.database.models import Document

def ingest_pdf_document(
    file_path: str,
    title: str,
    db: Session,
    source_url: str = "",
    issuing_authority: str = "महाराष्ट्र शासन / Government of Maharashtra",
    publication_date: str = "",
    doc_id: str = None
) -> Dict[str, Any]:
    """
    Complete Document Ingestion Pipeline:
    PDF Upload -> Validation -> Page Text Extraction (OCR Fallback) -> Chunking -> Vector Indexing -> SQLite Metadata.
    """
    path_obj = Path(file_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    filename = path_obj.name
    file_size_kb = round(os.path.getsize(file_path) / 1024.0, 2)

    # Create or update document record in database
    if doc_id:
        doc_record = db.query(Document).filter(Document.id == doc_id).first()
    else:
        doc_record = None

    if not doc_record:
        doc_record = Document(
            title=title or filename,
            filename=filename,
            file_path=str(path_obj.resolve()),
            source_url=source_url,
            issuing_authority=issuing_authority,
            publication_date=publication_date,
            processing_status="processing",
            file_size_kb=file_size_kb
        )
        db.add(doc_record)
        db.commit()
        db.refresh(doc_record)

    try:
        logger.info(f"Extracting text from {filename} (Doc ID: {doc_record.id})...")
        pages = extract_text_from_pdf(str(path_obj))

        total_extracted_chars = sum(p["char_count"] for p in pages)
        ocr_pages_count = sum(1 for p in pages if p["is_ocr"])

        logger.info(f"Extracted {len(pages)} pages ({total_extracted_chars} characters, {ocr_pages_count} OCR-scanned pages).")

        # Create semantic chunks
        chunks = chunk_document_pages(
            pages=pages,
            doc_id=doc_record.id,
            title=doc_record.title,
            issuing_authority=doc_record.issuing_authority,
            chunk_size=settings.CHUNK_SIZE_CHARS,
            chunk_overlap=settings.CHUNK_OVERLAP_CHARS
        )

        if not chunks:
            raise ValueError("No readable text could be extracted or chunked from document.")

        # Index in FAISS
        added_vectors = faiss_retriever.add_chunks(chunks)

        # Update document record
        doc_record.processing_status = "indexed"
        doc_record.chunk_count = added_vectors
        db.commit()

        return {
            "document_id": doc_record.id,
            "title": doc_record.title,
            "filename": doc_record.filename,
            "pages_count": len(pages),
            "ocr_pages_count": ocr_pages_count,
            "chunk_count": added_vectors,
            "status": "indexed"
        }

    except Exception as e:
        logger.error(f"Ingestion failed for {filename}: {e}")
        doc_record.processing_status = "failed"
        doc_record.error_message = str(e)
        db.commit()
        raise

