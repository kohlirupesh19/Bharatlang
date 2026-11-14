"""Multi-level government tables: rowspan/colspan headers, caption rows and column-number rows.

The fixture is the real Surya HTML of the 2025 PMFBY GR, PDF page 46 (Ratnagiri).
"""
from backend.app.services.rag.corpus.ocr_blocks import Block, blocks_from_surya_page, parse_table, parse_table_with_context
from backend.app.services.rag.corpus.structured_chunker import DocMeta, chunk_blocks, render_row

PMFBY_HTML = (
    '<table>'
    '<tr><th colspan="12">प्रधानमंत्री पीक विमा योजना खरीप हंगाम २०२५</th></tr>'
    '<tr><th colspan="12">विमा संरक्षित रक्कम, विमा हप्ता दर इ. तपशिल</th></tr>'
    '<tr><th colspan="12">प्रपत्र अ - ४</th></tr>'
    '<tr><td colspan="2">समूह क्र. : ५</td><td colspan="4">विमा कंपनीचे नाव : भारतीय कृषि बिमा कंपनी लि.</td>'
    '<td colspan="6">जिल्हा : रत्नागिरी</td></tr>'
    '<tr><th rowspan="2">अ.क्र.</th><th rowspan="2">पीक</th>'
    '<th colspan="4">विमा संरक्षण प्रति हे. (उंबरठा उत्पन्न पातळीपर्यन्त)</th>'
    '<th colspan="2">शेतकरी हिस्सा प्रति हे.</th><th colspan="2">केंद्र हिस्सा प्रति हे.</th>'
    '<th colspan="2">राज्य हिस्सा प्रति हे.</th></tr>'
    '<tr><th>जोखीमस्तर (टक्के)</th><th>विमा संरक्षित रक्कम (रु.)</th><th>विमा हप्ता दर (टक्के)</th>'
    '<th>विमा हप्ता रक्कम (रु.)</th><th>विमा हप्ता दर (टक्के)</th><th>विमा हप्ता रक्कम (रु.)</th>'
    '<th>विमा हप्ता दर (टक्के)</th><th>विमा हप्ता अनुदान रक्कम (रु.)</th><th>विमा हप्ता दर (टक्के)</th>'
    '<th>विमा हप्ता अनुदान रक्कम (रु.)</th></tr>'
    '<tr>' + "".join(f"<td>{d}</td>" for d in "१ २ ३ ४ ५ ६ ७ ८ ९ १० ११ १२".split()) + '</tr>'
    '<tr><td>१</td><td>भात (तांदूळ)</td><td>७०</td><td>६१०००</td><td>०.७५</td><td>४५७.५०</td><td>०.७५</td>'
    '<td>४५७.५०</td><td>०.०००</td><td>०.००</td><td>०.०००</td><td>०.००</td></tr>'
    '<tr><td>२</td><td>नाचणी</td><td>७०</td><td>३५०००</td><td>०.२५</td><td>८७.५०</td><td>०.२५</td>'
    '<td>८७.५०</td><td>०.०००</td><td>०.००</td><td>०.०००</td><td>०.००</td></tr>'
    '</table>'
)

COVER = "विमा संरक्षण प्रति हे. (उंबरठा उत्पन्न पातळीपर्यन्त)"
FARMER = "शेतकरी हिस्सा प्रति हे."

META = DocMeta(
    doc_id="crop-revised-pmfby-2025-06-24", title="सुधारित प्रधानमंत्री पीक विमा योजना (PMFBY)", scheme="crop_insurance",
    gr_number="प्रपीवियो-2025/प्र.क्र.66/11-अे", issue_date="2025-06-24", status="current",
    source_url="https://example.gov.in/pmfby.pdf", language="mr", superseded_by=(), issuing_authority="कृषि विभाग",
)


def test_multilevel_header_gives_each_column_its_full_name():
    header, _rows = parse_table(PMFBY_HTML)
    assert len(header) == 12
    assert header[0] == "अ.क्र."
    assert header[1] == "पीक"
    assert header[3] == f"{COVER} › विमा संरक्षित रक्कम (रु.)"
    assert header[7] == f"{FARMER} › विमा हप्ता रक्कम (रु.)"


def test_caption_rows_become_context_not_data():
    context, (_header, rows) = parse_table_with_context(PMFBY_HTML)
    assert context == (
        "प्रधानमंत्री पीक विमा योजना खरीप हंगाम २०२५",
        "विमा संरक्षित रक्कम, विमा हप्ता दर इ. तपशिल",
        "प्रपत्र अ - ४",
        "समूह क्र. : ५ | विमा कंपनीचे नाव : भारतीय कृषि बिमा कंपनी लि. | जिल्हा : रत्नागिरी",
    )
    assert [r[1] for r in rows] == ["भात (तांदूळ)", "नाचणी"]  # column-number row dropped


def test_rows_align_values_with_the_right_columns():
    header, rows = parse_table(PMFBY_HTML)
    rice = dict(zip(header, rows[0]))
    assert rice[f"{COVER} › विमा संरक्षित रक्कम (रु.)"] == "६१०००"
    assert rice[f"{COVER} › विमा हप्ता रक्कम (रु.)"] == "४५७.५०"


def test_render_row_groups_sub_columns_under_their_parent_once():
    header, rows = parse_table(PMFBY_HTML)
    line = render_row(header, rows[0])
    assert line.startswith("अ.क्र.: १; पीक: भात (तांदूळ); ")
    assert f"{COVER}: जोखीमस्तर (टक्के) ७०, विमा संरक्षित रक्कम (रु.) ६१०००," in line
    assert line.count(COVER) == 1


def test_every_table_chunk_names_its_district_and_titles_its_section():
    page = {"page": 46, "blocks": [
        {"label": "SectionHeader", "html": "<h2>अर्जदाराचा तपशील</h2>", "reading_order": 0},
        {"label": "Table", "html": PMFBY_HTML, "reading_order": 1},
    ]}
    chunks = chunk_blocks(blocks_from_surya_page(page), META, max_chars=900)
    tables = [c for c in chunks if c["chunk_type"] == "table"]
    assert len(tables) == 2  # one crop row per chunk at this budget
    for chunk in tables:
        assert "जिल्हा : रत्नागिरी" in chunk["text"]
        assert "अर्जदाराचा तपशील" not in chunk["text"]  # stale heading from a previous page
        assert chunk["section"].startswith("प्रधानमंत्री पीक विमा योजना खरीप हंगाम २०२५")
        assert len(chunk["text"]) <= 900
    assert "विमा संरक्षित रक्कम (रु.) ६१०००" in tables[0]["text"]


def test_simple_table_without_caption_is_unchanged():
    html = ("<table><tr><th>अ.क्र.</th><th>रक्कम</th></tr>"
            "<tr><td>१</td><td>रु. २०००/-</td></tr></table>")
    context, (header, rows) = parse_table_with_context(html)
    assert context == ()
    assert header == ["अ.क्र.", "रक्कम"]
    assert rows == [["१", "रु. २०००/-"]]


def test_full_width_row_inside_data_is_kept_as_plain_label():
    html = ("<table><tr><th>पीक</th><th>दर</th></tr>"
            "<tr><td colspan=\"2\">खरीप</td></tr>"
            "<tr><td>भात</td><td>२%</td></tr></table>")
    header, rows = parse_table(html)
    assert rows == [["खरीप"], ["भात", "२%"]]
    assert render_row(header, rows[0]) == "खरीप"


def test_rowspan_data_cell_repeats_into_following_rows():
    html = ("<table><tr><th>विभाग</th><th>पीक</th></tr>"
            "<tr><td rowspan=\"2\">कोकण</td><td>भात</td></tr>"
            "<tr><td>नाचणी</td></tr></table>")
    _header, rows = parse_table(html)
    assert rows == [["कोकण", "भात"], ["कोकण", "नाचणी"]]


BARE_TABLE_HTML = PMFBY_HTML.replace(
    '<tr><th colspan="12">प्रधानमंत्री पीक विमा योजना खरीप हंगाम २०२५</th></tr>'
    '<tr><th colspan="12">विमा संरक्षित रक्कम, विमा हप्ता दर इ. तपशिल</th></tr>'
    '<tr><th colspan="12">प्रपत्र अ - ४</th></tr>'
    '<tr><td colspan="2">समूह क्र. : ५</td><td colspan="4">विमा कंपनीचे नाव : भारतीय कृषि बिमा कंपनी लि.</td>'
    '<td colspan="6">जिल्हा : रत्नागिरी</td></tr>', "")


def _split_caption_page():
    """PDF p49 layout: Surya emitted the caption as headings + short text blocks above a bare table."""
    return {"page": 49, "blocks": [
        {"label": "SectionHeader", "html": "<p>प्रधानमंत्री पीक विमा योजना खरीप हंगाम २०२५</p>", "reading_order": 1},
        {"label": "SectionHeader", "html": "<p>प्रपत्र अ - ७</p>", "reading_order": 2},
        {"label": "Text", "html": "<p>समूह क्र. : ८</p>", "reading_order": 3},
        {"label": "Text", "html": "<p>जिल्हा : धुळे</p>", "reading_order": 4},
        {"label": "Table", "html": BARE_TABLE_HTML, "reading_order": 5},
    ]}


def test_split_caption_above_bare_table_becomes_its_context():
    blocks = blocks_from_surya_page(_split_caption_page())
    table = [b for b in blocks if b.kind == "table"][0]
    assert table.context == ("प्रधानमंत्री पीक विमा योजना खरीप हंगाम २०२५", "प्रपत्र अ - ७",
                             "समूह क्र. : ८", "जिल्हा : धुळे")
    assert [b.kind for b in blocks] == ["heading", "heading", "table"]  # caption text not duplicated


def test_split_caption_reaches_every_row_chunk():
    chunks = chunk_blocks(blocks_from_surya_page(_split_caption_page()), META, max_chars=900)
    tables = [c for c in chunks if c["chunk_type"] == "table"]
    assert len(tables) == 2
    assert all("जिल्हा : धुळे" in c["text"] and "खरीप हंगाम २०२५" in c["text"] for c in tables)


def test_long_paragraph_above_table_is_not_absorbed():
    long_text = "या योजनेअंतर्गत " + "पात्र शेतकऱ्यांना लाभ देण्यात येईल. " * 10
    page = {"page": 3, "blocks": [
        {"label": "Text", "html": f"<p>{long_text}</p>", "reading_order": 1},
        {"label": "Table", "html": BARE_TABLE_HTML, "reading_order": 2},
    ]}
    blocks = blocks_from_surya_page(page)
    assert [b.kind for b in blocks] == ["text", "table"]
    assert blocks[1].context == ()


def test_lead_in_sentence_above_table_stays_prose():
    page = {"page": 2, "blocks": [
        {"label": "Text", "html": "<p>खालील वेळापत्रकाप्रमाणे लाभ वितरीत करण्यात येईल.</p>", "reading_order": 1},
        {"label": "Table", "html": BARE_TABLE_HTML, "reading_order": 2},
    ]}
    blocks = blocks_from_surya_page(page)
    assert [b.kind for b in blocks] == ["text", "table"]
    assert blocks[1].context == ()


def test_inflated_ocr_colspans_do_not_break_header_detection():
    # PDF p48 (Nashik): Surya gave title rows colspan=13 and the caption row 7+4+3=14 on a 12-column table.
    html = (PMFBY_HTML
            .replace('colspan="12">प्रधानमंत्री', 'colspan="13">प्रधानमंत्री')
            .replace('<td colspan="2">समूह', '<td colspan="7">समूह')
            .replace('<td colspan="6">जिल्हा', '<td colspan="3">जिल्हा'))
    context, (header, rows) = parse_table_with_context(html)
    assert len(header) == 12
    assert header[1] == "पीक"
    assert header[3] == f"{COVER} › विमा संरक्षित रक्कम (रु.)"
    assert context[-1].endswith("जिल्हा : रत्नागिरी")
    assert [r[1] for r in rows] == ["भात (तांदूळ)", "नाचणी"]


def test_block_context_is_immutable_tuple():
    blocks = blocks_from_surya_page({"page": 1, "blocks": [{"label": "Table", "html": PMFBY_HTML}]})
    assert isinstance(blocks[0], Block)
    assert isinstance(blocks[0].context, tuple)
