import io
import os
import re
from pathlib import Path
from typing import List, Dict, Any
import pymupdf
import pytesseract
from PIL import Image
from backend.app.core.config import settings
from backend.app.core.logging import logger

# Configure local tesseract data prefix
TESSDATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "tessdata"
if TESSDATA_DIR.exists():
    os.environ["TESSDATA_PREFIX"] = str(TESSDATA_DIR)

pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH

def clean_extracted_text(text: str) -> str:
    """
    Cleans raw PDF or OCR text:
    - Normalizes unicode characters
    - Fixes hyphenated line breaks
    - Consolidates redundant whitespace while preserving paragraph breaks
    """
    if not text:
        return ""
    
    # Fix broken hyphenated words at line endings
    cleaned = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
    # Replace multiple spaces with single space
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)
    # Replace excessive line breaks (more than 2) with double newline
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()

def extract_text_from_pdf(pdf_path: str, min_chars_for_native: int = 40) -> List[Dict[str, Any]]:
    """
    Extracts text page-by-page from a PDF document.
    If a page has insufficient native text (scanned document),
    it transparently falls back to Tesseract OCR with Marathi, Hindi, and English models.
    
    Returns a list of dictionaries:
    [
        {
            "page": 1,
            "text": "...",
            "char_count": 520,
            "is_ocr": False
        },
        ...
    ]
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

    doc = pymupdf.open(pdf_path)
    pages_data = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        raw_text = page.get_text("text") or ""
        cleaned = clean_extracted_text(raw_text)
        is_ocr = False

        # If page has little or no text, it is likely a scanned document
        if len(cleaned) < min_chars_for_native:
            logger.info(f"Page {page_num + 1} has insufficient native text ({len(cleaned)} chars). Falling back to OCR...")
            try:
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                
                # Run OCR with marathi, hindi and english
                ocr_text = pytesseract.image_to_string(img, lang="mar+hin+eng")
                ocr_cleaned = clean_extracted_text(ocr_text)
                if len(ocr_cleaned) > len(cleaned):
                    cleaned = ocr_cleaned
                    is_ocr = True
            except Exception as ocr_err:
                logger.warning(f"OCR fallback failed on page {page_num + 1}: {ocr_err}")

        pages_data.append({
            "page": page_num + 1,
            "text": cleaned,
            "char_count": len(cleaned),
            "is_ocr": is_ocr
        })

    doc.close()
    return pages_data

