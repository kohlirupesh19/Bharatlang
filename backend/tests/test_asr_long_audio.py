"""Long utterances are decoded in pause-delimited pieces so Whisper cannot drop their end.

Whisper decodes a 30 s window with a 448-token budget; Devanagari Marathi exhausts it after
roughly 220 characters, so a 20-25 s question lost its last 8-12 words (the actual question)
mid-word. Measured 2026-11-12 on 4 read-aloud clips: pooled WER 22.3% -> 8.4% when split
into <=14 s pieces at pauses; audio of 14 s or less keeps the original single decode.
"""
import numpy as np
import pytest

from backend.app.services.asr.long_audio import AudioPiece, plan_pieces

SR = 16000


def stamps(*spans_s):
    return [{"start": int(a * SR), "end": int(b * SR)} for a, b in spans_s]


def seconds(pieces):
    return [(round(p.start / SR, 2), round(p.end / SR, 2)) for p in pieces]


def test_long_speech_is_cut_at_the_pause_nearest_the_limit():
    # 25 s read-aloud: sentences separated by short pauses.
    speech = stamps((0.3, 4.0), (4.5, 8.2), (8.6, 12.6), (13.1, 17.0), (17.4, 21.0), (21.5, 24.8))
    pieces = plan_pieces(speech, total_samples=25 * SR, sample_rate=SR, max_piece_s=14.0, pad_s=0.2)
    assert len(pieces) == 2
    assert pieces[0].end <= pieces[1].start  # no overlap, no duplicated words
    assert all((p.end - p.start) / SR <= 14.0 + 2 * 0.2 for p in pieces)
    # the cut falls in the 12.6-13.1 s pause, not inside speech
    assert 12.6 * SR <= pieces[0].end <= 13.1 * SR
    assert 12.6 * SR <= pieces[1].start <= 13.1 * SR


def test_padding_never_crosses_the_midpoint_of_a_short_pause():
    speech = stamps((0.0, 10.0), (10.2, 20.0))
    pieces = plan_pieces(speech, total_samples=21 * SR, sample_rate=SR, max_piece_s=14.0, pad_s=0.2)
    assert seconds(pieces) == [(0.0, 10.1), (10.1, 20.2)]


def test_padding_is_clipped_to_the_audio():
    speech = stamps((0.05, 13.0), (13.5, 24.99))
    pieces = plan_pieces(speech, total_samples=25 * SR, sample_rate=SR, max_piece_s=14.0, pad_s=0.2)
    assert pieces[0].start == 0
    assert pieces[-1].end == 25 * SR


def test_speech_that_fits_is_one_piece():
    speech = stamps((0.5, 5.0), (5.6, 12.0))
    pieces = plan_pieces(speech, total_samples=13 * SR, sample_rate=SR, max_piece_s=14.0, pad_s=0.2)
    assert seconds(pieces) == [(0.3, 12.2)]


def test_no_speech_gives_no_pieces():
    assert plan_pieces([], total_samples=20 * SR, sample_rate=SR, max_piece_s=14.0, pad_s=0.2) == ()


def test_a_single_region_longer_than_the_limit_is_kept_not_dropped():
    speech = stamps((1.0, 17.0), (17.5, 20.0))
    pieces = plan_pieces(speech, total_samples=21 * SR, sample_rate=SR, max_piece_s=14.0, pad_s=0.2)
    assert len(pieces) == 2
    assert pieces[0] == AudioPiece(round(0.8 * SR), round(17.2 * SR))


# --- engine wiring (needs faster-whisper; runs on the office box) -------------------------

class _Seg:
    def __init__(self, start, end, text):
        self.start, self.end, self.text, self.avg_logprob = start, end, text, -0.1


class _Info:
    language, language_probability = "mr", 0.99


class _FakeModel:
    """Returns one segment per call naming the length of audio it was given."""

    def __init__(self):
        self.calls = []

    def transcribe(self, audio, **kwargs):
        self.calls.append(len(audio))
        secs = len(audio) / SR
        return iter([_Seg(0.0, secs, f"भाग{len(self.calls)}")]), _Info()


@pytest.fixture
def engine(monkeypatch):
    pytest.importorskip("faster_whisper")
    from backend.app.services.asr import whisper
    eng = whisper.FasterWhisperEngine(model_path=None, display_name="fake", prompt_bias=False,
                                      condition_on_previous_text=False)
    eng.model, eng._is_loaded = _FakeModel(), True
    monkeypatch.setattr(whisper.settings, "ASR_MAX_PIECE_SEC", 14.0)
    return eng, whisper


def test_short_audio_is_decoded_whole_as_before(engine, monkeypatch):
    eng, whisper = engine
    monkeypatch.setattr(whisper, "find_speech", lambda *_: pytest.fail("VAD split used for short audio"))
    result = eng.transcribe(np.zeros(10 * SR, dtype=np.float32))
    assert eng.model.calls == [10 * SR]
    assert result.recognized_text == "भाग1"


def test_long_audio_is_decoded_piece_by_piece_on_the_original_timeline(engine, monkeypatch):
    eng, whisper = engine
    monkeypatch.setattr(whisper, "find_speech",
                        lambda audio, sr, max_s: stamps((0.3, 12.6), (13.1, 24.8)))
    result = eng.transcribe(np.zeros(25 * SR, dtype=np.float32))
    assert len(eng.model.calls) == 2
    assert result.recognized_text == "भाग1 भाग2"
    assert [s.id for s in result.segments] == [0, 1]
    second = result.segments[1]
    assert second.start == pytest.approx(12.9, abs=0.01)  # offset by where the piece starts
    assert second.end == pytest.approx(25.0, abs=0.01)
    assert result.metadata["pieces"] == 2


def test_long_audio_with_one_short_speech_region_is_decoded_whole(engine, monkeypatch):
    # e.g. 8 s of speech inside 20 s of audio: it fits one window, so no split is needed.
    eng, whisper = engine
    monkeypatch.setattr(whisper, "find_speech", lambda *_: stamps((6.0, 14.0)))
    result = eng.transcribe(np.zeros(20 * SR, dtype=np.float32))
    assert eng.model.calls == [20 * SR]
    assert result.metadata["pieces"] == 1


def test_long_audio_without_detected_speech_falls_back_to_one_decode(engine, monkeypatch):
    eng, whisper = engine
    monkeypatch.setattr(whisper, "find_speech", lambda *_: [])
    eng.transcribe(np.zeros(20 * SR, dtype=np.float32))
    assert eng.model.calls == [20 * SR]
