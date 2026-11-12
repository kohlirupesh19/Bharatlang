"""Tests for structured OCR ingestion: block parsing, table rows, section-aware chunks, quality gate."""
import pytest

from backend.app.services.rag.corpus.ocr_blocks import Block, blocks_from_surya_page, html_to_text, parse_table
from backend.app.services.rag.corpus.quality import QualityError, check_text_quality
from backend.app.services.rag.corpus.structured_chunker import DocMeta, chunk_blocks

TABLE_HTML = (
    "<table><tr><th>अ.क्र.</th><th>हप्ता क्रमांक</th><th>कालावधी</th><th>रक्कम</th></tr>"
    "<tr><td>१</td><td>पहिला हप्ता</td><td>माहे एप्रिल ते जुलै</td><td>रु. २०००/-</td></tr>"
    "<tr><td>२</td><td>दुसरा हप्ता</td><td>माहे ऑगस्ट ते नोव्हेंबर</td><td>रु. २०००/-</td></tr></table>"
)

SURYA_PAGE = {
    "page": 2,
    "blocks": [
        {"label": "PageHeader", "html": "<p>शासन निर्णय क्रमांक: किसनि-२०२३/प्र.क्र.४२/११-अे</p>", "reading_order": 0},
        {"label": "SectionHeader", "html": "<h2>४. निधी वितरणाची कार्यपद्धती:-</h2>", "reading_order": 1},
        {"label": "Text", "html": "<p>खालील वेळापत्रकाप्रमाणे लाभ <b>थेट</b> हस्तांतरणाद्वारे वितरीत करण्यात येईल.</p>", "reading_order": 2},
        {"label": "Table", "html": TABLE_HTML, "reading_order": 3},
        {"label": "PageFooter", "html": "<p>पृष्ठ ४ पैकी २</p>", "reading_order": 4},
    ],
}

META = DocMeta(
    doc_id="namo-2023-06-15", title="नमो शेतकरी महासन्मान निधी", scheme="namo_shetkari",
    gr_number="किसनि-२०२३/प्र.क्र.४२/११-अे", issue_date="2023-06-15", status="current",
    source_url="https://example.gov.in/namo.pdf", language="mr", superseded_by=(),
    issuing_authority="कृषि विभाग",
)


class TestHtmlParsing:
    def test_html_to_text_strips_tags_and_keeps_line_breaks(self):
        assert html_to_text("<p>पहिली ओळ<br/>दुसरी <b>ओळ</b></p>") == "पहिली ओळ\nदुसरी ओळ"

    def test_html_to_text_turns_list_items_into_lines(self):
        assert html_to_text("<ol><li>i. एक</li><li>ii. दोन</li></ol>") == "i. एक\nii. दोन"

    def test_parse_table_returns_header_and_rows(self):
        header, rows = parse_table(TABLE_HTML)
        assert header == ["अ.क्र.", "हप्ता क्रमांक", "कालावधी", "रक्कम"]
        assert rows[0] == ["१", "पहिला हप्ता", "माहे एप्रिल ते जुलै", "रु. २०००/-"]
        assert len(rows) == 2

    def test_blocks_from_page_drops_headers_and_footers_and_orders(self):
        blocks = blocks_from_surya_page(SURYA_PAGE)
        assert [b.kind for b in blocks] == ["heading", "text", "table"]
        assert all(b.page == 2 for b in blocks)


class TestChunking:
    def test_table_rows_carry_column_headers_and_section(self):
        chunks = chunk_blocks(blocks_from_surya_page(SURYA_PAGE), META, max_chars=2000)
        table_chunks = [c for c in chunks if c["chunk_type"] == "table"]
        assert table_chunks, "expected a table chunk"
        text = table_chunks[0]["text"]
        assert "हप्ता क्रमांक: पहिला हप्ता" in text
        assert "रक्कम: रु. २०००/-" in text
        assert "निधी वितरणाची कार्यपद्धती" in text  # section context

    def test_chunks_have_context_prefix_and_metadata(self):
        chunks = chunk_blocks(blocks_from_surya_page(SURYA_PAGE), META, max_chars=2000)
        first = chunks[0]
        assert first["text"].startswith("नमो शेतकरी महासन्मान निधी")
        for key in ("chunk_id", "doc_id", "page", "section", "scheme", "gr_number", "issue_date",
                    "status", "source_url", "title", "issuing_authority"):
            assert key in first
        assert len({c["chunk_id"] for c in chunks}) == len(chunks)

    def test_footer_text_never_reaches_chunks(self):
        chunks = chunk_blocks(blocks_from_surya_page(SURYA_PAGE), META, max_chars=2000)
        assert not any("पृष्ठ ४ पैकी २" in c["text"] for c in chunks)

    def test_long_section_is_split_without_exceeding_budget(self):
        para = "शेतकऱ्यांना लाभ मिळेल. " * 60
        blocks = [Block(1, "heading", "१. पात्रता", None), Block(1, "text", para, None)]
        chunks = chunk_blocks(blocks, META, max_chars=400)
        assert len(chunks) > 1
        assert all(len(c["text"]) <= 400 for c in chunks)
        assert all("१. पात्रता" in c["text"] for c in chunks)

    def test_text_spanning_pages_keeps_correct_page_numbers(self):
        blocks = [Block(1, "text", "पहिल्या पानावरील मजकूर.", None),
                  Block(2, "text", "दुसऱ्या पानावरील मजकूर.", None),
                  Block(3, "text", "तिसऱ्या पानावरील मजकूर.", None)]
        chunks = chunk_blocks(blocks, META, max_chars=2000)
        pages = {c["page"] for c in chunks}
        assert pages == {1, 2, 3}
        assert any("दुसऱ्या" in c["text"] and c["page"] == 2 for c in chunks)

    def test_large_table_is_split_by_rows_with_header_repeated(self):
        header = ["जिल्हा", "पीक", "विमा हप्ता दर"]
        rows = [[f"जिल्हा{i}", "सोयाबीन", "२%"] for i in range(80)]
        blocks = [Block(5, "table", "", (header, rows))]
        chunks = chunk_blocks(blocks, META, max_chars=600)
        assert len(chunks) > 1
        assert all("पीक: सोयाबीन" in c["text"] for c in chunks)
        assert all(len(c["text"]) <= 600 for c in chunks)


class TestQualityGate:
    def test_accepts_real_marathi(self):
        check_text_quality("नमो शेतकरी महासन्मान निधी योजनेत वर्षाला सहा हजार रुपये मिळतात.", "mr", "doc")

    def test_rejects_dot_corrupted_marathi(self):
        with pytest.raises(QualityError):
            check_text_quality("·········· ···· ····, (Namo Shetkari Mahasanman Nidhi Scheme) ·······", "mr", "doc")

    def test_rejects_marathi_doc_with_little_devanagari(self):
        with pytest.raises(QualityError):
            check_text_quality("This text is supposed to be Marathi but is English.", "mr", "doc")

    def test_english_docs_are_not_held_to_devanagari_ratio(self):
        check_text_quality("Individuals who paid income tax in the last assessment year are excluded.", "en", "doc")
