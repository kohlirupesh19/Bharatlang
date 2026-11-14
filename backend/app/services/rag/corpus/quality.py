"""Reject corpus text that is not genuine script, e.g. legacy-font garbage or '·' placeholders."""

MIN_DEVANAGARI_RATIO = 0.6
MAX_PLACEHOLDER_RATIO = 0.02
_PLACEHOLDERS = "·�□"  # middle dot, replacement char, white square


class QualityError(ValueError):
    pass


def devanagari_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if "ऀ" <= c <= "ॿ") / len(letters)


def check_text_quality(text: str, language: str, doc_id: str) -> None:
    visible = [c for c in text if not c.isspace()]
    if not visible:
        raise QualityError(f"{doc_id}: no text extracted")
    placeholder_ratio = sum(1 for c in visible if c in _PLACEHOLDERS) / len(visible)
    if placeholder_ratio > MAX_PLACEHOLDER_RATIO:
        raise QualityError(f"{doc_id}: {placeholder_ratio:.1%} placeholder glyphs (corrupted extraction)")
    if language == "mr":
        ratio = devanagari_ratio(text)
        if ratio < MIN_DEVANAGARI_RATIO:
            raise QualityError(f"{doc_id}: only {ratio:.1%} Devanagari letters in a Marathi document")
