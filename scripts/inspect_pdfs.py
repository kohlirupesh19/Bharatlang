"""Report whether each PDF has machine-readable Devanagari or needs OCR."""
import hashlib
import sys
from pathlib import Path

import pymupdf

sys.stdout.reconfigure(encoding="utf-8")


def devanagari_ratio(text: str) -> tuple[int, float]:
    letters = [c for c in text if c.isalpha()]
    deva = sum(1 for c in letters if 0x0900 <= ord(c) <= 0x097F)
    return deva, (deva / len(letters)) if letters else 0.0


for pdf in sorted(Path(sys.argv[1]).rglob("*.pdf")):
    doc = pymupdf.open(pdf)
    text = "".join(page.get_text() for page in doc)
    deva, ratio = devanagari_ratio(text)
    images = sum(len(page.get_images()) for page in doc)
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()[:16]
    print(f"\n== {pdf.relative_to(sys.argv[1])}  pages={len(doc)} chars={len(text)} devanagari={deva} ratio={ratio:.2f} images={images} sha256={sha}")
    print("  fonts:", sorted({f[3] for page in doc for f in page.get_fonts()})[:6])
    print("  first text:", " ".join(text.split())[:300])
