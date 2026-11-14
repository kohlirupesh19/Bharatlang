"""Tests for the ASR benchmark's text normaliser and statistics."""
import pytest

from backend.app.evaluation.asr_bench.normalize import normalize_marathi
from backend.app.evaluation.asr_bench.stats import (
    UtteranceScore,
    corpus_error_rates,
    paired_bootstrap,
    score_utterance,
    speaker_bootstrap_ci,
)


class TestNormalizeMarathi:
    def test_strips_punctuation_and_danda(self):
        assert normalize_marathi("बकरी किंवा मेंढीपासून खत मिळते का ?") == "बकरी किंवा मेंढीपासून खत मिळते का"
        assert normalize_marathi("हे खरे आहे। ते ॥") == "हे खरे आहे ते"

    def test_maps_devanagari_digits_to_ascii(self):
        assert normalize_marathi("₹६,००० मिळतात") == "6000 मिळतात"

    def test_keeps_digit_groups_but_drops_thousands_separators(self):
        assert normalize_marathi("2,000 रुपये") == "2000 रुपये"

    def test_precomposed_and_decomposed_nukta_forms_match(self):
        # U+0958 is a composition exclusion: NFC decomposes it to क + nukta.
        assert normalize_marathi("क़") == normalize_marathi("क़")

    def test_removes_zero_width_joiners_and_collapses_spaces(self):
        assert normalize_marathi("  क्‍ष   आणि‌  ") == "क्ष आणि"

    def test_lowercases_latin(self):
        assert normalize_marathi("PM-KISAN योजना") == "pm kisan योजना"

    def test_empty_input(self):
        assert normalize_marathi("   ") == ""


class TestScoring:
    def test_score_utterance_counts_word_and_char_edits(self):
        s = score_utterance("u1", "spk", "मला कर्ज हवे", "मला कर्ज हवं")
        assert s.ref_words == 3
        assert s.word_errors == 1
        assert s.ref_chars > 0 and s.char_errors >= 1

    def test_empty_hypothesis_is_all_deletions(self):
        s = score_utterance("u1", "spk", "एक दोन", "")
        assert s.word_errors == 2

    def test_corpus_rates_are_edit_weighted_not_averaged(self):
        scores = [
            UtteranceScore("a", "s1", 10, 0, 40, 0),
            UtteranceScore("b", "s2", 2, 2, 8, 8),
        ]
        rates = corpus_error_rates(scores)
        assert rates["wer"] == pytest.approx(2 / 12)
        assert rates["cer"] == pytest.approx(8 / 48)

    def test_corpus_rates_reject_empty_input(self):
        with pytest.raises(ValueError):
            corpus_error_rates([])


class TestBootstrap:
    def _scores(self, errors_per_speaker):
        out = []
        for spk, errs in errors_per_speaker.items():
            for i, e in enumerate(errs):
                out.append(UtteranceScore(f"{spk}-{i}", spk, 10, e, 40, e * 4))
        return out

    def test_speaker_ci_brackets_point_estimate(self):
        scores = self._scores({"a": [1, 2], "b": [0, 1], "c": [3, 2], "d": [1, 1]})
        ci = speaker_bootstrap_ci(scores, n_resamples=500, seed=0)
        assert ci["wer_low"] <= ci["wer"] <= ci["wer_high"]

    def test_paired_bootstrap_detects_clear_improvement(self):
        base = self._scores({s: [4, 5, 4] for s in "abcdefgh"})
        better = self._scores({s: [1, 1, 2] for s in "abcdefgh"})
        result = paired_bootstrap(base, better, n_resamples=500, seed=0)
        assert result["delta_wer"] < 0
        assert result["delta_wer_high"] < 0
        assert result["p_improvement"] > 0.99

    def test_paired_bootstrap_requires_same_utterances(self):
        a = self._scores({"a": [1]})
        b = self._scores({"b": [1]})
        with pytest.raises(ValueError):
            paired_bootstrap(a, b, n_resamples=10, seed=0)
