"""Public list of the corpus documents: what citizens see, read from manifest.json."""
import json

import pytest

from backend.app.services.rag.corpus.sources import (
    CorpusSourcesError,
    load_corpus_sources,
)

NAMO = {
    "doc_id": "namo-2023-06-15",
    "scheme": "namo_shetkari",
    "title": "नमो शेतकरी महासन्मान निधी",
    "gr_number": "किसनि-२०२३/प्र.क्र.४२/११-अे",
    "department": "कृषि विभाग",
    "issue_date": "2023-06-15",
    "language": "mr",
    "status": "current",
    "path": "sources/namo_shetkari/GR.pdf",
    "url": "https://gr.maharashtra.gov.in/Site/Upload/x.pdf",
    "sha256": "abc",
    "notes": "internal note",
    "ocr_pages": None,
}
OLD_CROP = {
    "doc_id": "crop-2024",
    "title": "सर्वसमावेशक पिक विमा",
    "department": "कृषि विभाग",
    "issue_date": "2024-02-13",
    "language": "mr",
    "status": "superseded",
    "superseded_by": ["crop-2025"],
    "url": "https://gr.maharashtra.gov.in/old.pdf",
}


def _write(tmp_path, documents):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"version": 1, "documents": documents}, ensure_ascii=False), encoding="utf-8")
    return path


def test_lists_public_fields_only(tmp_path):
    [source] = load_corpus_sources(_write(tmp_path, [NAMO]))
    dumped = source.model_dump()
    assert dumped == {
        "doc_id": "namo-2023-06-15",
        "title": "नमो शेतकरी महासन्मान निधी",
        "gr_number": "किसनि-२०२३/प्र.क्र.४२/११-अे",
        "department": "कृषि विभाग",
        "issue_date": "2023-06-15",
        "language": "mr",
        "status": "current",
        "url": "https://gr.maharashtra.gov.in/Site/Upload/x.pdf",
    }


def test_current_documents_come_first_then_newest(tmp_path):
    newer = {**NAMO, "doc_id": "n2", "issue_date": "2025-01-01"}
    undated = {**NAMO, "doc_id": "n3", "issue_date": None}
    sources = load_corpus_sources(_write(tmp_path, [OLD_CROP, NAMO, undated, newer]))
    assert [s.doc_id for s in sources] == ["n2", "namo-2023-06-15", "n3", "crop-2024"]


def test_non_https_url_is_dropped(tmp_path):
    [source] = load_corpus_sources(_write(tmp_path, [{**NAMO, "url": "javascript:alert(1)"}]))
    assert source.url is None


def test_missing_manifest_raises(tmp_path):
    with pytest.raises(CorpusSourcesError):
        load_corpus_sources(tmp_path / "absent.json")


@pytest.mark.parametrize("bad", [
    {**NAMO, "title": ""},
    {**NAMO, "status": "draft"},
    {**NAMO, "issue_date": "15/06/2023"},
    {**NAMO, "issue_date": "20230615"},
    {**NAMO, "issue_date": "2023-W24-4"},
    {k: v for k, v in NAMO.items() if k != "doc_id"},
])
def test_invalid_entries_raise(tmp_path, bad):
    with pytest.raises(CorpusSourcesError):
        load_corpus_sources(_write(tmp_path, [bad]))


def test_duplicate_doc_ids_raise(tmp_path):
    with pytest.raises(CorpusSourcesError, match="duplicate"):
        load_corpus_sources(_write(tmp_path, [NAMO, {**NAMO, "title": "again"}]))


def test_real_manifest_loads():
    from backend.app.core.config import settings

    sources = load_corpus_sources(settings.DOCUMENTS_DIR / "manifest.json")
    assert len(sources) >= 7
    assert all(s.url is None or s.url.startswith("https://") for s in sources)


def _client():
    from fastapi.testclient import TestClient

    from backend.app.main import app

    return TestClient(app)


def test_sources_endpoint_returns_public_list(tmp_path, monkeypatch):
    from backend.app.core.config import settings

    _write(tmp_path, [OLD_CROP, NAMO])
    monkeypatch.setattr(settings, "DOCUMENTS_DIR", tmp_path)
    response = _client().get("/api/documents/sources")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [d["doc_id"] for d in body["documents"]] == ["namo-2023-06-15", "crop-2024"]
    assert "path" not in body["documents"][0] and "sha256" not in body["documents"][0]


def test_sources_endpoint_503_when_manifest_missing(tmp_path, monkeypatch):
    from backend.app.core.config import settings

    monkeypatch.setattr(settings, "DOCUMENTS_DIR", tmp_path)
    response = _client().get("/api/documents/sources")
    assert response.status_code == 503
    assert "manifest" not in response.json()["detail"]
