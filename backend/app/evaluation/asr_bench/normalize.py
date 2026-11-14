"""The one text normaliser applied to every reference and hypothesis before scoring.

Changing it invalidates comparisons with earlier runs, so it carries a version tag that
is written into every run summary.
"""
import re
import unicodedata

NORMALIZER_VERSION = "mr-norm-v1"

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_ZERO_WIDTH = re.compile("[​‌‍⁠﻿]")
_THOUSANDS_SEP = re.compile(r"(?<=\d)[,٬](?=\d)")
_WHITESPACE = re.compile(r"\s+")


def _is_separator(ch: str) -> bool:
    """Punctuation (incl. danda ।॥) and symbols (incl. ₹) become word breaks."""
    return unicodedata.category(ch)[0] in ("P", "S")


def normalize_marathi(text: str) -> str:
    """NFC, drop zero-width marks, ASCII digits, strip punctuation/symbols, lowercase Latin."""
    text = unicodedata.normalize("NFC", text)
    text = _ZERO_WIDTH.sub("", text)
    text = text.translate(_DEVANAGARI_DIGITS)
    text = _THOUSANDS_SEP.sub("", text)
    text = "".join(" " if _is_separator(ch) else ch for ch in text)
    text = text.lower()
    return _WHITESPACE.sub(" ", text).strip()
