"""Shared fixtures for the evidence gate and table lookup: PMFBY-style rate-table chunks
(district context + one row per crop) and state-wide prose chunks."""
from backend.app.services.rag.entity_lexicon import build_lexicon
from backend.app.services.rag.evidence_gate import build_corpus_scope
from backend.app.services.rag.table_lookup import build_table_index

TITLE = "सुधारित प्रधानमंत्री पीक विमा योजना (PMFBY) खरीप हंगाम 2025 व रब्बी हंगाम 2025-26 करीता राज्यात राबविणेबाबत"
HEADER = "प्रधानमंत्री पीक विमा योजना खरीप हंगाम २०२५ | विमा संरक्षित रक्कम, विमा हप्ता दर इ. तपशिल | जिल्हा: {district}"


def table_chunk(district: str, *crops_and_amounts: tuple, chunk_id: str = "") -> dict:
    rows = "\n".join(f"अ.क्र.: {i}; पीक: {crop}; विमा संरक्षित रक्कम (रु.) {amount}"
                     for i, (crop, amount) in enumerate(crops_and_amounts, 1))
    return {"chunk_id": chunk_id or f"{district}-{len(rows)}", "chunk_type": "table", "doc_id": "pmfby-2025",
            "text": f"{TITLE}\n{HEADER.format(district=district)}\n{rows}"}


RATNAGIRI = table_chunk("रत्नागिरी", ("भात (तांदूळ)", "६१०००"), ("नाचणी", "४००००"))
THANE = table_chunk("ठाणे", ("भात (तांदूळ)", "६१०००"), ("उ. भुईमूग", "४२०००"))
LATUR = table_chunk("लातूर", ("सोयाबीन", "५८०००"), ("तूर", "४७०००"))
NASHIK = table_chunk("नाशिक", ("कापूस", "६००००"), ("सोयाबीन", "५५०००"), ("गहू बा.", "४५०००"))
GADCHIROLI = table_chunk("गडचिरोली", ("कापूस", "५९०००"), ("भात (तांदूळ)", "५५०००"))
# A state-wide prose chunk: the GR address names Mumbai, which must not scope it to a district.
NAMO_TEXT = {"chunk_id": "namo:p1:c1", "chunk_type": "text", "doc_id": "namo-2023",
             "text": "नमो शेतकरी महासन्मान निधी\nमंत्रालय, मुंबई ४०० ०३२\nपात्र शेतकरी कुटुंबास प्रतिवर्षी रु. ६०००/- लाभ देण्यात येईल."}
# PMFBY prose: same (district-specific) document as the tables, but no district of its own.
PMFBY_TEXT = {"chunk_id": "pmfby:p3:c18", "chunk_type": "text", "doc_id": "pmfby-2025",
              "text": f"{TITLE}\nखरीप हंगामात भात, सोयाबीन, कापूस इ. अधिसूचित पिकांसाठी योजना राबविण्यात येईल."}
KARJ_TEXT = {"chunk_id": "karj:p1:c3", "chunk_type": "text", "doc_id": "karj-2019",
             "text": "कर्जमुक्ती योजना\nअल्पमुदत पीक कर्जाची थकबाकी रु. २ लाखापर्यंत माफ करण्यात येईल."}
CORPUS = [RATNAGIRI, THANE, LATUR, NASHIK, GADCHIROLI, NAMO_TEXT, PMFBY_TEXT, KARJ_TEXT]
LEXICON = build_lexicon(c["text"] for c in CORPUS)
CORPUS_SCOPE = build_corpus_scope(CORPUS, LEXICON)
TABLES = build_table_index(CORPUS, LEXICON)
