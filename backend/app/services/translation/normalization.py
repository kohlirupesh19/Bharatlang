import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from backend.app.services.translation.dialect_lexicon import (
    COLLOQUIAL_NORMALIZATIONS,
    DATIVE_RULE_EXCEPTIONS,
    GLOSSARY_MARATHI_ENGLISH,
    INFINITIVE_VERB_STEMS,
    OBLIGATION_AUXILIARY_STEM,
    OBLIGATION_VERB_FORMS,
    RECEIVE_ENDINGS,
    RECEIVE_STEM_COLLOQUIAL,
    RECEIVE_STEM_STANDARD,
    VARHADI_STRONG_MARKERS,
    VARHADI_TO_STANDARD_MARATHI,
)

__all__ = [
    "GLOSSARY_MARATHI_ENGLISH",
    "VARHADI_TO_STANDARD_MARATHI",
    "detect_language_and_dialect",
    "normalize_varhadi_to_marathi",
]

# How strongly a rewrite indicates Varhadi.
KIND_STRONG = "varhadi"        # form not used in standard Marathi
KIND_WEAK = "colloquial_verb"  # colloquial usage common in Vidarbha but heard elsewhere
KIND_NEUTRAL = "colloquial"    # informal spelling, no dialect evidence

MARKER_WEIGHTS: Dict[str, float] = {KIND_STRONG: 1.0, KIND_WEAK: 0.5, KIND_NEUTRAL: 0.0}

# A sentence is Varhadi when it has at least one strong marker AND either enough
# total evidence or enough evidence relative to its length. One stray marker in a
# long sentence (often an ASR slip) is not enough.
VARHADI_MIN_ABSOLUTE_SCORE = 2.0
VARHADI_MIN_DENSITY = 0.10

LATIN_DOMINANCE_RATIO = 0.65
CODE_SWITCH_MIN_CHARS = 3

# Devanagari letters, signs and digits, excluding danda (U+0964) and double danda (U+0965).
_DEVANAGARI_WORD = r'[ऀ-ॣ०-ॿ]'
_TOKEN_PATTERN = re.compile(rf'^(.*?)({_DEVANAGARI_WORD}+)(.*)$', re.DOTALL)

_VERB_INFINITIVE_SUFFIX = "ाले"
_VERB_INFINITIVE_STANDARD = "ायला"
_VARHADI_AYLE_SUFFIX = "ायले"
_PLURAL_DATIVE_SUFFIX = "्यायले"
_PLURAL_DATIVE_STANDARD = "्यांना"
_SINGULAR_DATIVE_SUFFIX = "्याले"
_SINGULAR_DATIVE_STANDARD = "्याला"


@dataclass(frozen=True)
class _Rewrite:
    normalized: str
    kind: str
    rule: str


@dataclass(frozen=True)
class _Token:
    prefix: str
    core: str
    suffix: str
    rewrite: Optional[_Rewrite]

    @property
    def is_word(self) -> bool:
        return bool(self.core)

    def render(self) -> str:
        core = self.rewrite.normalized if self.rewrite else self.core
        return f"{self.prefix}{core}{self.suffix}"


def _split_token(raw: str) -> Tuple[str, str, str]:
    """Splits a whitespace token into (leading punctuation, Devanagari word, trailing rest)."""
    match = _TOKEN_PATTERN.match(raw)
    if not match:
        return raw, "", ""
    return match.group(1), match.group(2), match.group(3)


def _rewrite_receive_verb(word: str) -> Optional[_Rewrite]:
    if not word.startswith(RECEIVE_STEM_COLLOQUIAL):
        return None
    ending = word[len(RECEIVE_STEM_COLLOQUIAL):]
    standard_ending = RECEIVE_ENDINGS.get(ending)
    if standard_ending is None:
        return None
    return _Rewrite(f"{RECEIVE_STEM_STANDARD}{standard_ending}", KIND_WEAK, "receive_verb")


def _rewrite_by_suffix(word: str) -> Optional[_Rewrite]:
    """Suffix rules for Varhadi forms that are not listed word by word."""
    if word.endswith(_PLURAL_DATIVE_SUFFIX):
        stem = word[:-len(_PLURAL_DATIVE_SUFFIX)]
        if stem:
            return _Rewrite(f"{stem}{_PLURAL_DATIVE_STANDARD}", KIND_STRONG, "plural_dative")

    if word.endswith(_VARHADI_AYLE_SUFFIX):
        stem = word[:-len(_VARHADI_AYLE_SUFFIX)]
        if stem:
            return _Rewrite(f"{stem}{_VERB_INFINITIVE_STANDARD}", KIND_STRONG, "infinitive")

    if word.endswith(_SINGULAR_DATIVE_SUFFIX) and word not in DATIVE_RULE_EXCEPTIONS:
        stem = word[:-len(_SINGULAR_DATIVE_SUFFIX)]
        if stem:
            return _Rewrite(f"{stem}{_SINGULAR_DATIVE_STANDARD}", KIND_STRONG, "dative")

    if word.endswith(_VERB_INFINITIVE_SUFFIX):
        stem = word[:-len(_VERB_INFINITIVE_SUFFIX)]
        if stem in INFINITIVE_VERB_STEMS:
            return _Rewrite(f"{stem}{_VERB_INFINITIVE_STANDARD}", KIND_STRONG, "infinitive")

    return None


def _rewrite_word(word: str, next_word: str) -> Optional[_Rewrite]:
    """Decides how one word should be rewritten, most specific evidence first."""
    if word in VARHADI_STRONG_MARKERS:
        return _Rewrite(VARHADI_STRONG_MARKERS[word], KIND_STRONG, "lexicon")

    if word in OBLIGATION_VERB_FORMS and next_word.startswith(OBLIGATION_AUXILIARY_STEM):
        return _Rewrite(OBLIGATION_VERB_FORMS[word], KIND_STRONG, "obligation")

    if word in COLLOQUIAL_NORMALIZATIONS:
        return _Rewrite(COLLOQUIAL_NORMALIZATIONS[word], KIND_NEUTRAL, "lexicon")

    return _rewrite_receive_verb(word) or _rewrite_by_suffix(word)


def _analyze(text: str) -> List[_Token]:
    """Tokenizes text and attaches the rewrite (if any) for every word. Shared by detection and normalization."""
    canonical = unicodedata.normalize("NFC", text)
    parts = [_split_token(raw) for raw in canonical.split()]
    tokens: List[_Token] = []
    for i, (prefix, core, suffix) in enumerate(parts):
        next_core = parts[i + 1][1] if i + 1 < len(parts) else ""
        rewrite = _rewrite_word(core, next_core) if core else None
        if rewrite is not None and rewrite.normalized == core:
            rewrite = None
        tokens.append(_Token(prefix, core, suffix, rewrite))
    return tokens


def detect_language_and_dialect(text: str) -> Dict[str, Any]:
    """
    Detects whether text is Standard Marathi, Varhadi dialect,
    Marathi-English code-switched, or English.
    Varhadi is decided by weighted marker evidence, not by a single word hit.
    """
    if not text or not text.strip():
        return {
            "primary_language": "unknown",
            "dialect": "unknown",
            "is_code_switched": False,
            "varhadi_score": 0.0
        }

    devanagari_chars = len(re.findall(_DEVANAGARI_WORD, text))
    latin_chars = len(re.findall(r'[a-zA-Z]', text))
    total_chars = max(len(re.sub(r'\s', '', text)), 1)

    is_predominantly_latin = (latin_chars / total_chars) > LATIN_DOMINANCE_RATIO
    is_code_switched = (latin_chars > CODE_SWITCH_MIN_CHARS) and (devanagari_chars > CODE_SWITCH_MIN_CHARS)

    if is_predominantly_latin:
        return {
            "primary_language": "en",
            "dialect": "Standard English",
            "is_code_switched": is_code_switched,
            "varhadi_score": 0.0
        }

    tokens = _analyze(text)
    word_count = max(sum(1 for t in tokens if t.is_word), 1)
    rewrites = [(t.core, t.rewrite) for t in tokens if t.rewrite is not None]

    strong_markers = [core for core, rw in rewrites if rw.kind == KIND_STRONG]
    weak_markers = [core for core, rw in rewrites if rw.kind == KIND_WEAK]
    evidence = sum(MARKER_WEIGHTS[rw.kind] for _, rw in rewrites)
    density = evidence / word_count

    is_varhadi = bool(strong_markers) and (
        evidence >= VARHADI_MIN_ABSOLUTE_SCORE or density >= VARHADI_MIN_DENSITY
    )

    return {
        "primary_language": "mr",
        "dialect": "Varhadi (Vidarbha)" if is_varhadi else "Standard Marathi",
        "is_code_switched": is_code_switched,
        "varhadi_score": round(density, 3),
        "detected_markers": strong_markers + weak_markers,
        "strong_marker_count": len(strong_markers),
        "weak_marker_count": len(weak_markers)
    }


def normalize_varhadi_to_marathi(original_text: str) -> Tuple[str, List[Dict[str, str]]]:
    """
    Normalizes Varhadi dialectal expressions into standard Marathi for downstream processing.
    CRITICAL: Preserves the original text completely and returns substitutions separately.
    Does not replace names, numbers, or standard words.
    """
    if not original_text:
        return "", []

    tokens = _analyze(original_text)
    normalized_text = " ".join(t.render() for t in tokens)
    replacements_made = [
        {
            "original": t.core,
            "normalized": t.rewrite.normalized,
            "kind": t.rewrite.kind,
            "rule": t.rewrite.rule
        }
        for t in tokens if t.rewrite is not None
    ]
    return normalized_text, replacements_made
