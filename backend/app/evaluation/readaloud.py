"""Read-aloud test set scoring: meaning kept, answer correct, and (diagnostic) WER.

Speakers read fixed paragraphs (vault: docs/eval/multi_speaker_read_aloud.md). A reader may
skip or change the odd word, which is fine as long as the meaning survives, so a clip is
judged on what the app needs:

1. meaning kept: the asked district and crop (as the evidence gate reads them, via
   `EntityLexicon.find_asked`) and the key phrases of the question survive in the transcript;
2. answer correct: the reply contains every gold figure, or refuses where the corpus has no
   answer (traps);
3. WER, strict (benchmark normaliser) and loose (number words as digits, spelling variants
   folded), only to diagnose the ASR. Reader deviations count against both.
"""
import re
from dataclasses import dataclass
from typing import Dict, FrozenSet, Optional, Sequence, Tuple

from backend.app.evaluation.asr_bench.normalize import normalize_marathi
from backend.app.services.rag.entity_lexicon import EntityLexicon, fold
from backend.app.services.rag.evidence_gate import REFUSAL
from backend.app.services.rag.numeric_guard import extract_numbers, normalize_digits

Phrases = Tuple[Tuple[str, ...], ...]  # every group must match; any alternative in a group will do

ENGLISH_REFUSAL = "The available official documents do not contain sufficient evidence"

INSURANCE: Phrases =(("खरीप", "खरिप"), ("2025", "दोन हजार पंचवीस"))
SUM_INSURED = ("संरक्षित",)
PREMIUM = ("हप्त", "हफ्त", "हिस्स")
INSTALMENT = ("हप्त", "हफ्त")


@dataclass(frozen=True)
class ItemSpec:
    """What a paragraph asks and what the right answer contains (gold table in the vault note)."""
    district: Optional[str] = None
    crop: Optional[str] = None
    phrases: Phrases = ()
    gold: Phrases = ()  # figures/words the answer must contain; empty when it must refuse
    refuse: bool = False


ITEMS: Dict[str, ItemSpec] = {
    "C01": ItemSpec(phrases=(("नमो",), ("वर्षा", "वर्षी"), INSTALMENT),
                    gold=(("6000", "सहा हजार"), ("2000", "दोन हजार"))),
    "C02": ItemSpec("रत्नागिरी", "भात", (*INSURANCE, SUM_INSURED), gold=(("61000",),)),
    "C03": ItemSpec("नाशिक", "सोयाबीन", (*INSURANCE, PREMIUM), gold=(("817.5",),)),
    "C04": ItemSpec("गडचिरोली", "कापूस", (*INSURANCE, SUM_INSURED), gold=(("59000",),)),
    "C05": ItemSpec(phrases=(("कर्जमुक्ती",), ("माफ",)), gold=(("200000", "2 लाख", "दोन लाख"),)),
    "C06": ItemSpec(phrases=(("प्रोत्साहन",), ("जास्त",)), gold=(("50000", "50 हजार", "पन्नास हजार"),)),
    "C07": ItemSpec("बीड", "कापूस", (*INSURANCE, PREMIUM), gold=(("1800",),)),
    "C08": ItemSpec("सोलापूर", "ज्वारी", (*INSURANCE, SUM_INSURED, PREMIUM), gold=(("28175",), ("70.44",))),
    "C09": ItemSpec("जळगाव", "कापूस", (*INSURANCE, SUM_INSURED), gold=(("48400",),)),
    "C10": ItemSpec("ठाणे", "सोयाबीन", (*INSURANCE, PREMIUM), refuse=True),
    "C11": ItemSpec(phrases=(("सौर",), ("पंप",), ("अनुदान",)), refuse=True),
    "C12": ItemSpec(phrases=(("नमो",), ("पहिला", "पहिल्या"), INSTALMENT, ("महिन",)),
                    gold=(("2000",), ("एप्रिल",), ("जुलै",))),
    "V01": ItemSpec("अमरावती", "सोयाबीन", (PREMIUM,), gold=(("559",),)),
    "V02": ItemSpec("यवतमाळ", "कापूस", (SUM_INSURED, PREMIUM), gold=(("60000",), ("750",))),
    "V03": ItemSpec("अकोला", "सोयाबीन", (SUM_INSURED,), gold=(("58000",),)),
    "V04": ItemSpec("वाशिम", "सोयाबीन", (PREMIUM,), gold=(("870",),)),
    "V05": ItemSpec(phrases=(("प्रोत्साहन", "फेड"),), gold=(("50000", "50 हजार", "पन्नास हजार"),)),
    "V06": ItemSpec("बुलढाणा", "डाळिंब", (PREMIUM,), refuse=True),
}

# Number phrases the paragraphs spell out, as ASR writes them. Generic Marathi number words are
# numeric-guard-v2 work; these cover the set's text.
_NUMBER_PHRASES = (("दोन लाख चाळीस हजार", "240000 "), ("दोन हजार पंचवीस", "2025 "), ("दोन हजार सोळा", "2016 "))
_SPELLING = (("हफ्त", "हप्त"),)


def loose_normalize(text: str) -> str:
    """Benchmark normaliser plus: spelled-out numbers as digits, spelling variants folded."""
    for words, digits in _NUMBER_PHRASES:
        text = text.replace(words, digits)
    text = normalize_marathi(text)
    for variant, standard in _SPELLING:
        text = text.replace(variant, standard)
    return " ".join(fold(word) for word in text.split())


def _word_errors(reference: Sequence[str], hypothesis: Sequence[str]) -> int:
    """Levenshtein distance over words (substitutions + deletions + insertions)."""
    previous = list(range(len(hypothesis) + 1))
    for i, ref_word in enumerate(reference, 1):
        current = [i]
        for j, hyp_word in enumerate(hypothesis, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ref_word != hyp_word)))
        previous = current
    return previous[-1]


def loose_word_errors(reference: str, hypothesis: str) -> Tuple[int, int, int]:
    """(strict errors, loose errors, reference words under the benchmark normaliser)."""
    strict_ref = normalize_marathi(reference).split()
    strict = _word_errors(strict_ref, normalize_marathi(hypothesis).split())
    loose = _word_errors(loose_normalize(reference).split(), loose_normalize(hypothesis).split())
    return strict, loose, len(strict_ref)


_NUMERIC = re.compile(r"[\d.,]+")


def _numbers(text: str) -> FrozenSet[str]:
    """Whole numbers in canonical form ("५९,०००" -> "59000", "817.50" -> "817.5"), spelled-out ones too."""
    for words, digits in _NUMBER_PHRASES:
        text = text.replace(words, digits)
    return frozenset(extract_numbers(normalize_digits(text)))


def _has(normalized: str, numbers: FrozenSet[str], alternative: str) -> bool:
    """Numbers must match a whole number; phrases must start at a word boundary (stems may inflect)."""
    if _NUMERIC.fullmatch(normalize_digits(alternative)):
        return extract_numbers(alternative) <= numbers
    return re.search(r"(?<!\S)" + re.escape(loose_normalize(alternative)), normalized) is not None


def _missing(text: str, groups: Phrases) -> Tuple[str, ...]:
    normalized, numbers = loose_normalize(text), _numbers(text)
    return tuple(group[0] for group in groups if not any(_has(normalized, numbers, alt) for alt in group))


@dataclass(frozen=True)
class MeaningReport:
    """district_ok/crop_ok: the expected entity is among those the gate will treat as asked.

    The gate errs towards asking (an indirect question in the backstory, "कितले कापले ते कळत
    न्हाई", also asks its nearest crop), so extra asked entities are reported, not failed; they
    can only cost a refusal, which the end-to-end answer check then shows.
    """
    district_ok: bool
    crop_ok: bool
    missing_phrases: Tuple[str, ...]
    heard_districts: Tuple[str, ...]
    heard_crops: Tuple[str, ...]
    extra_asked: Tuple[str, ...] = ()

    @property
    def kept(self) -> bool:
        return self.district_ok and self.crop_ok and not self.missing_phrases


def meaning_check(transcript: str, spec: ItemSpec, lexicon: EntityLexicon) -> MeaningReport:
    """Would the app understand the same question from this transcript?"""
    asked = lexicon.find_asked(transcript)
    expected = {spec.district, spec.crop} - {None}
    return MeaningReport(
        district_ok=spec.district is None or spec.district in asked.districts,
        crop_ok=spec.crop is None or spec.crop in asked.crops,
        missing_phrases=_missing(transcript, spec.phrases),
        heard_districts=tuple(sorted(asked.districts)),
        heard_crops=tuple(sorted(asked.crops)),
        extra_asked=tuple(sorted((asked.districts | asked.crops) - expected)) if expected else (),
    )


@dataclass(frozen=True)
class AnswerReport:
    correct: bool
    refused: bool
    missing_gold: Tuple[str, ...]


def answer_check(answer: str, spec: ItemSpec) -> AnswerReport:
    """Every gold figure present (any accepted form), or a refusal where the corpus has none.

    Only the app's fixed refusal (Marathi, or its English half) counts as refusing; a trap
    answered with an LLM-worded "not available" is not credited.
    """
    refused = REFUSAL.rstrip(".") in answer or ENGLISH_REFUSAL in answer
    if spec.refuse:
        return AnswerReport(correct=refused, refused=refused, missing_gold=())
    missing = _missing(answer, spec.gold)
    return AnswerReport(correct=not refused and not missing, refused=refused, missing_gold=missing)


_HEADING = re.compile(r"^### (\S+)", re.MULTILINE)


def parse_paragraphs(note: str) -> Dict[str, str]:
    """Marathi text of each item in the vault note's "## Paragraphs" section (EN: lines dropped)."""
    body = note.split("## Paragraphs", 1)[1].split("\n## ", 1)[0]
    paragraphs = {}
    blocks = _HEADING.split(body)[1:]
    for item, block in zip(blocks[::2], blocks[1::2]):
        lines = [l.strip() for l in block.splitlines()[1:] if l.strip() and not l.startswith("EN:")]
        paragraphs[item] = " ".join(lines)
    return paragraphs
