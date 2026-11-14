"""Numeric faithfulness guard.

A wrong rupee amount or rate is the most harmful answer this system can give, and local
LLMs misread Devanagari numerals (e.g. ६१००० returned as "६,१००"). Every substantive
number in an answer (3+ digits, or any decimal) must appear in the retrieved evidence or
the question; anything else is reported so the answer can carry an explicit warning.
"""
import re
from decimal import Decimal, InvalidOperation
from typing import Iterable, Optional, Set, Tuple

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
# Digits with Indian or Western grouping commas and an optional decimal part.
_NUMBER = re.compile(r"(?<![\d.])\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|(?<![\d.,])\d+(?:\.\d+)?")


def normalize_digits(text: str) -> str:
    return text.translate(_DEVANAGARI_DIGITS)


def _canonical(raw: str) -> Optional[str]:
    try:
        value = Decimal(raw.replace(",", ""))
    except InvalidOperation:
        return None
    text = format(value.normalize(), "f")
    return text


def _numbers_in_order(text: str) -> Tuple[str, ...]:
    found = (_canonical(m.group()) for m in _NUMBER.finditer(normalize_digits(text)))
    return tuple(n for n in found if n is not None)


def extract_numbers(text: str) -> Set[str]:
    return set(_numbers_in_order(text))


def _is_substantive(number: str) -> bool:
    return "." in number or len(number) >= 3


def unverified_numbers(answer: str, evidence: Iterable[str], question: Optional[str] = None) -> Tuple[str, ...]:
    allowed: Set[str] = set()
    for text in [*evidence, question or ""]:
        allowed |= extract_numbers(text)
    flagged = []
    for number in _numbers_in_order(answer):
        if _is_substantive(number) and number not in allowed and number not in flagged:
            flagged.append(number)
    return tuple(flagged)
