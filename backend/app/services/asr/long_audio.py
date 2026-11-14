"""Split long audio at pauses so each piece fits one Whisper decoding window.

Whisper decodes a 30 s window with a 448-token budget. Marathi in Devanagari uses that up
after roughly 220 characters, so a 20-25 s question lost its last words (usually the question
itself) mid-word. Pieces of at most ~14 s, cut in pauses found by VAD, each get the full
budget and are padded to 30 s the way Whisper was trained (2026-11-12, 4 read-aloud clips:
pooled WER 22.3% -> 8.4%; a shorter `chunk_length` window gave 12.8%).

Known limit: if someone speaks for longer than the limit without any pause, Silero has to cut
inside speech, and the word at that cut can be garbled. Read and conversational speech
pauses far more often than that.

This module only plans the cuts; it has no model dependency.
"""
from dataclasses import dataclass
from typing import List, Mapping, Sequence, Tuple


@dataclass(frozen=True)
class AudioPiece:
    start: int  # sample index, inclusive
    end: int    # sample index, exclusive


def _group(speech: Sequence[Mapping[str, int]], max_samples: int) -> List[Tuple[int, int]]:
    """Consecutive speech regions merged while the merged span stays within max_samples."""
    groups: List[Tuple[int, int]] = []
    for region in speech:
        start, end = int(region["start"]), int(region["end"])
        if groups and end - groups[-1][0] <= max_samples:
            groups[-1] = (groups[-1][0], end)
        else:
            groups.append((start, end))  # a region longer than the limit stays whole
    return groups


def plan_pieces(
    speech: Sequence[Mapping[str, int]],
    total_samples: int,
    sample_rate: int,
    max_piece_s: float,
    pad_s: float,
) -> Tuple[AudioPiece, ...]:
    """Pieces covering the speech regions, each padded by pad_s.

    Padding stops at the audio edges and at the midpoint of the pause to the neighbouring
    piece, so pieces never overlap (an overlap would transcribe the same words twice).
    """
    groups = _group(speech, int(round(max_piece_s * sample_rate)))
    pad = int(round(pad_s * sample_rate))
    pieces = []
    for i, (start, end) in enumerate(groups):
        lower = 0 if i == 0 else (groups[i - 1][1] + start) // 2
        upper = total_samples if i == len(groups) - 1 else (end + groups[i + 1][0]) // 2
        pieces.append(AudioPiece(max(lower, start - pad), min(upper, end + pad)))
    return tuple(pieces)
