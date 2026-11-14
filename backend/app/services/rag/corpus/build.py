"""Rebuild the retrieval index from the frozen corpus manifest.

  python -m backend.app.services.rag.corpus.build            # build + replace index
  python -m backend.app.services.rag.corpus.build --dry-run  # chunk + report only
"""
import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pymupdf

from backend.app.core.config import settings
from backend.app.services.rag.corpus.corrections import CorrectionError, apply_corrections, parse_corrections
from backend.app.services.rag.corpus.ocr_blocks import Block, blocks_from_surya_results, remap_to_pdf_pages
from backend.app.services.rag.corpus.quality import QualityError, check_text_quality
from backend.app.services.rag.corpus.structured_chunker import DocMeta, chunk_blocks

DOCS_DIR = settings.DOCUMENTS_DIR
MANIFEST = DOCS_DIR / "manifest.json"
OCR_DIR = DOCS_DIR / "ocr"
REPORT = settings.INDEXES_DIR / "corpus_report.json"
MAX_CHUNK_CHARS = 900
E5_MAX_TOKENS = 512


def text_layer_blocks(pdf_path: Path) -> List[Block]:
    """For PDFs with a clean embedded text layer (checked by the quality gate)."""
    blocks: List[Block] = []
    with pymupdf.open(pdf_path) as doc:
        for page_no, page in enumerate(doc, start=1):
            for *_bbox, text, _block_no, block_type in page.get_text("blocks"):
                text = " ".join(text.split())
                if block_type == 0 and text:
                    blocks.append(Block(page_no, "text", text, None))
    return blocks


def load_blocks(doc: Dict) -> List[Block]:
    if doc["ocr_pages"] == "text-layer":
        return text_layer_blocks(DOCS_DIR / doc["path"])
    results = sorted((OCR_DIR / doc["doc_id"]).rglob("results.json"))
    if not results:
        raise FileNotFoundError(f"{doc['doc_id']}: no OCR results under {OCR_DIR / doc['doc_id']}")
    try:
        blocks = remap_to_pdf_pages(blocks_from_surya_results(results[0]), doc["ocr_pages"])
    except ValueError as exc:
        raise CorrectionError(f"{doc['doc_id']}: {exc}") from exc
    # Correction pages are real (1-based) PDF pages, as printed when verifying against the PDF.
    return apply_corrections(blocks, parse_corrections(doc), doc["doc_id"])


def doc_meta(doc: Dict) -> DocMeta:
    return DocMeta(
        doc_id=doc["doc_id"], title=doc["title"], scheme=doc["scheme"], gr_number=doc.get("gr_number"),
        issue_date=doc.get("issue_date"), status=doc["status"], source_url=doc["url"],
        language=doc["language"], superseded_by=tuple(doc.get("superseded_by", [])),
        issuing_authority=doc.get("department") or "",
    )


def token_lengths(texts: List[str]) -> List[int]:
    from backend.app.services.rag.embeddings import embedding_engine
    embedding_engine.load_model()
    tokenizer = embedding_engine.model.tokenizer
    return [len(tokenizer(f"passage: {t}", add_special_tokens=True)["input_ids"]) for t in texts]


def build(dry_run: bool) -> Dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    all_chunks: List[Dict] = []
    report: Dict = {"built_at": datetime.now().isoformat(timespec="seconds"),
                    "manifest_snapshot": manifest["snapshot_date"], "documents": {}, "errors": {}}
    for doc in manifest["documents"]:
        try:
            blocks = load_blocks(doc)
            check_text_quality("\n".join(b.text or json.dumps(b.table, ensure_ascii=False) for b in blocks),
                               doc["language"], doc["doc_id"])
            chunks = chunk_blocks(blocks, doc_meta(doc), MAX_CHUNK_CHARS)
        except (FileNotFoundError, QualityError, CorrectionError) as exc:
            report["errors"][doc["doc_id"]] = str(exc)
            continue
        all_chunks.extend(chunks)
        report["documents"][doc["doc_id"]] = {
            "blocks": len(blocks), "chunks": len(chunks),
            "ocr_corrections": len(doc.get("ocr_corrections", [])),
            "table_chunks": sum(1 for c in chunks if c["chunk_type"] == "table"),
            "pages": sorted({c["page"] for c in chunks}),
        }
    if not all_chunks:
        raise RuntimeError(f"No chunks built; errors: {report['errors']}")

    lengths = token_lengths([c["text"] for c in all_chunks])
    report["tokens"] = {"max": max(lengths), "mean": round(sum(lengths) / len(lengths), 1),
                        "over_limit": sum(1 for n in lengths if n > E5_MAX_TOKENS)}
    report["total_chunks"] = len(all_chunks)

    if not dry_run:
        from backend.app.services.rag.retrieval import INDEX_FILE, METADATA_FILE, faiss_retriever
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        for f in (INDEX_FILE, METADATA_FILE):
            if f.exists():
                shutil.copy2(f, f.with_name(f"{f.stem}.backup-{stamp}{f.suffix}"))
        faiss_retriever.replace_all_chunks(all_chunks)
        report["index_replaced"] = True
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="chunk and report without touching the index")
    report = build(parser.parse_args(argv).dry_run)
    print(json.dumps({k: v for k, v in report.items() if k != "documents"}, indent=2, ensure_ascii=False))
    print(json.dumps(report["documents"], ensure_ascii=False))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
