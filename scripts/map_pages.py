"""Print a compact page map of a PDF: page number, table count, first characters."""
import sys
import pymupdf
sys.stdout.reconfigure(encoding="utf-8")
doc = pymupdf.open(sys.argv[1])
prev = None
for i, page in enumerate(doc, start=1):
    text = " ".join(page.get_text().split())
    head = text[:70]
    tables = len(page.find_tables().tables)
    key = (head[:20], tables > 0)
    if i <= 30 or key != prev or i == len(doc):
        print(f"{i:4d} tables={tables} chars={len(text):5d} | {head}")
    prev = key
