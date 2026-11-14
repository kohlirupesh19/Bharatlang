"""Corpus-level WER/CER with speaker-level bootstrap confidence intervals.

Speakers contribute many utterances, so utterances are not independent: every resample
draws whole speakers with replacement.
"""
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Sequence

import jiwer
import numpy as np


@dataclass(frozen=True)
class UtteranceScore:
    utt_id: str
    speaker: str
    ref_words: int
    word_errors: int
    ref_chars: int
    char_errors: int


def _edits(output) -> int:
    return output.substitutions + output.deletions + output.insertions


def score_utterance(utt_id: str, speaker: str, reference: str, hypothesis: str) -> UtteranceScore:
    """Score one already-normalised pair. An empty hypothesis counts as all deletions."""
    if not reference.strip():
        raise ValueError(f"Empty reference for utterance {utt_id}")
    ref_words = len(reference.split())
    if not hypothesis.strip():
        return UtteranceScore(utt_id, speaker, ref_words, ref_words, len(reference), len(reference))
    words = jiwer.process_words(reference, hypothesis)
    chars = jiwer.process_characters(reference, hypothesis)
    ref_chars = chars.hits + chars.substitutions + chars.deletions
    return UtteranceScore(utt_id, speaker, ref_words, _edits(words), ref_chars, _edits(chars))


def corpus_error_rates(scores: Sequence[UtteranceScore]) -> Dict[str, float]:
    """Edit-weighted rates: total errors / total reference units (not a mean of ratios)."""
    if not scores:
        raise ValueError("No utterance scores to aggregate")
    ref_w = sum(s.ref_words for s in scores)
    ref_c = sum(s.ref_chars for s in scores)
    return {
        "wer": sum(s.word_errors for s in scores) / ref_w,
        "cer": sum(s.char_errors for s in scores) / ref_c,
        "n_utterances": len(scores),
        "ref_words": ref_w,
    }


def _speaker_totals(scores: Sequence[UtteranceScore]) -> Dict[str, np.ndarray]:
    """Per-speaker [ref_words, word_errors, ref_chars, char_errors]."""
    totals: Dict[str, np.ndarray] = defaultdict(lambda: np.zeros(4, dtype=np.int64))
    for s in scores:
        totals[s.speaker] = totals[s.speaker] + np.array(
            [s.ref_words, s.word_errors, s.ref_chars, s.char_errors], dtype=np.int64
        )
    return dict(totals)


def _rates(matrix: np.ndarray) -> np.ndarray:
    """matrix: (resamples, 4) summed totals -> (resamples, 2) [wer, cer]."""
    return np.stack([matrix[:, 1] / matrix[:, 0], matrix[:, 3] / matrix[:, 2]], axis=1)


def _resample(n_speakers: int, n_resamples: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, n_speakers, size=(n_resamples, n_speakers))


def speaker_bootstrap_ci(
    scores: Sequence[UtteranceScore], n_resamples: int = 2000, seed: int = 0, alpha: float = 0.05
) -> Dict[str, float]:
    point = corpus_error_rates(scores)
    totals = _speaker_totals(scores)
    table = np.stack(list(totals.values()))
    idx = _resample(len(table), n_resamples, seed)
    boot = _rates(table[idx].sum(axis=1))
    lo, hi = np.quantile(boot, [alpha / 2, 1 - alpha / 2], axis=0)
    return {
        "wer": point["wer"], "wer_low": float(lo[0]), "wer_high": float(hi[0]),
        "cer": point["cer"], "cer_low": float(lo[1]), "cer_high": float(hi[1]),
        "n_speakers": len(table), "n_utterances": point["n_utterances"],
    }


def paired_bootstrap(
    baseline: Sequence[UtteranceScore],
    candidate: Sequence[UtteranceScore],
    n_resamples: int = 2000,
    seed: int = 0,
    alpha: float = 0.05,
) -> Dict[str, float]:
    """Delta = candidate - baseline (negative is better), resampling shared speakers."""
    base_ids = {(s.utt_id, s.speaker) for s in baseline}
    if base_ids != {(s.utt_id, s.speaker) for s in candidate}:
        raise ValueError("Baseline and candidate must score the same utterances and speakers")
    speakers: List[str] = sorted({s.speaker for s in baseline})
    base_t, cand_t = _speaker_totals(baseline), _speaker_totals(candidate)
    base_tab = np.stack([base_t[s] for s in speakers])
    cand_tab = np.stack([cand_t[s] for s in speakers])
    idx = _resample(len(speakers), n_resamples, seed)
    delta = _rates(cand_tab[idx].sum(axis=1)) - _rates(base_tab[idx].sum(axis=1))
    lo, hi = np.quantile(delta, [alpha / 2, 1 - alpha / 2], axis=0)
    point = _rates(cand_tab.sum(axis=0, keepdims=True)) - _rates(base_tab.sum(axis=0, keepdims=True))
    return {
        "delta_wer": float(point[0, 0]), "delta_wer_low": float(lo[0]), "delta_wer_high": float(hi[0]),
        "delta_cer": float(point[0, 1]), "delta_cer_low": float(lo[1]), "delta_cer_high": float(hi[1]),
        "p_improvement": float((delta[:, 0] < 0).mean()), "n_speakers": len(speakers),
    }
