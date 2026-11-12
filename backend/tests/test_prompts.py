from backend.app.services.llm.prompts import build_rag_prompt


def _chunks(n, text="शब्द " * 400):
    return [{"title": f"योजना {i}", "page": i, "text": text} for i in range(1, n + 1)]


def test_prompt_includes_up_to_max_chunks():
    prompt = build_rag_prompt("प्रश्न?", _chunks(6), max_chunks=4, max_chars_per_chunk=200)
    assert "दस्तऐवज 4" in prompt
    assert "दस्तऐवज 5" not in prompt


def test_chunk_text_is_capped_per_chunk():
    short = build_rag_prompt("प्रश्न?", _chunks(1), max_chunks=1, max_chars_per_chunk=100)
    long = build_rag_prompt("प्रश्न?", _chunks(1), max_chunks=1, max_chars_per_chunk=600)
    assert len(long) - len(short) > 400


def test_short_chunk_is_passed_whole():
    prompt = build_rag_prompt("प्रश्न?", _chunks(1, text="पात्रता: दोन हेक्टरपर्यंत जमीन."))
    assert "पात्रता: दोन हेक्टरपर्यंत जमीन." in prompt


def test_original_wording_shown_only_when_it_differs():
    same = build_rag_prompt("मला पैसे पाहिजे", _chunks(1), original_query="मला पैसे पाहिजे")
    differs = build_rag_prompt("मला पैसे पाहिजे", _chunks(1), original_query="मले पयशे पायजे")
    assert "मूळ शब्द" not in same
    assert "मले पयशे पायजे" in differs


def test_empty_context_is_stated():
    assert "कोणताही संदर्भ सापडला नाही" in build_rag_prompt("प्रश्न?", [])


def test_devanagari_digits_reach_the_llm_as_ascii():
    chunk = {"title": "पीक विमा", "page": 46, "text": "विमा संरक्षित रक्कम (रु.) ६१०००, दर ०.७५"}
    prompt = build_rag_prompt("भात पिकासाठी २०२५ मध्ये रक्कम किती?", [chunk])
    assert "61000" in prompt and "0.75" in prompt and "2025" in prompt
    assert "६१०००" not in prompt


def test_document_title_is_not_repeated_inside_chunk_text():
    title = "सुधारित प्रधानमंत्री पीक विमा योजना"
    chunk = {"title": title, "page": 46, "text": f"{title}\nजिल्हा : रत्नागिरी\nपीक: भात"}
    prompt = build_rag_prompt("प्रश्न?", [chunk])
    assert prompt.count(title) == 1
    assert "जिल्हा : रत्नागिरी" in prompt
