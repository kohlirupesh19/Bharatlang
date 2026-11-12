"""Marathi lexicon of districts and crops, used to check that evidence matches a question.

Districts are a closed set (Maharashtra's 36), listed here with former names. Crops are an
open set: the lexicon is the common Maharashtra crops below plus every crop label found in
the indexed tables (`पीक:` cells), so a new GR extends it without code changes.

Matching is on "folded" text (spelling variants merged) and accepts Marathi inflection:
the oblique stem of names ending in -ा/-े (ठाणे → ठाण्यात, हरभरा → हरभऱ्याला) and a closed
set of case endings and postpositions (नाशिकमध्ये, भाताला, नागपुरले), so a look-alike word
such as धान्य (grain) is not taken for धान (paddy).
"""
import re
import unicodedata
from dataclasses import dataclass
from itertools import product
from typing import Dict, FrozenSet, Iterable, List, Mapping, Tuple

DISTRICTS: Mapping[str, Tuple[str, ...]] = {
    "अहिल्यानगर": ("अहिल्या नगर", "अहमदनगर"), "अकोला": (), "अमरावती": (),
    "छत्रपती संभाजीनगर": ("संभाजीनगर", "छत्रपती संभाजी नगर", "संभाजी नगर", "औरंगाबाद"), "बीड": (), "भंडारा": (), "बुलढाणा": (),
    "चंद्रपूर": (), "धाराशिव": ("उस्मानाबाद",), "धुळे": (), "गडचिरोली": (), "गोंदिया": (),
    "हिंगोली": (), "जळगाव": ("जलगाव",), "जालना": (), "कोल्हापूर": (), "लातूर": (),
    # One entry for both Mumbai districts (no farm tables exist for either), so a bare
    # "मुंबई" in a question is never compared against the wrong half.
    "मुंबई": ("मुंबई शहर", "मुंबई उपनगर"), "नागपूर": (), "नांदेड": (), "नंदुरबार": (),
    "नाशिक": ("नासिक",), "पालघर": (), "परभणी": (), "पुणे": (), "रायगड": (), "रत्नागिरी": (),
    "सांगली": (), "सातारा": (), "सिंधुदुर्ग": (), "सोलापूर": (), "ठाणे": (), "वर्धा": (),
    "वाशिम": (), "यवतमाळ": (),
}

# Synonyms and irregular oblique stems (कापूस → कापसाला, गहू → गव्हाला, उडीद → उडदाला,
# तांदूळ → तांदळाला, तूर → तुरीला).
# भुईमगू is a misspelling printed in the source (PMFBY GR 2025-06-24, p80, Nashik rabi
# table), not an OCR error, so it is aliased here rather than corrected in the manifest.
CROPS: Mapping[str, Tuple[str, ...]] = {
    "भात": ("धान", "तांदूळ", "तांदळ"), "कापूस": ("कापस", "कपाशी"), "सोयाबीन": (), "गहू": ("गव्ह",),
    "ज्वारी": (), "बाजरी": (), "मका": (), "नाचणी": ("नागली",), "तूर": ("तुरी",), "मूग": (),
    "उडीद": ("उडद",), "हरभरा": ("चणा", "चणे"), "भुईमूग": ("भुईमगू",), "तीळ": (), "कारळे": (), "सूर्यफूल": (),
    "करडई": (), "जवस": (), "कुळीथ": (), "कांदा": (), "ऊस": (), "हळद": ("हलद",), "डाळिंब": (),
    "द्राक्ष": ("द्राक्षे",), "केळी": (), "आंबा": (), "संत्रा": (), "मोसंबी": (), "काजू": (),
    "टोमॅटो": (),
}

# ण→न also absorbs a frequent ASR error (ठाणे heard as "ठाने"); measured on 3,957 RESPIN/FLEURS/GR
# texts it adds no false match. ळ→ल is NOT folded: "केली" (did) would become the crop केळी
# (135 false hits), so ळ variants are listed as targeted aliases instead (जलगाव, हलद).
_FOLD_MAP = str.maketrans({"ी": "ि", "ू": "ु", "ई": "इ", "ऊ": "उ", "ढ": "ड", "ऱ": "र", "ण": "न",
                           "ँ": None, "़": None, "‌": None, "‍": None})
# Anusvara is a real nasal before a stop (कांदा, संत्रा) but optional spelling before
# य-ह or at a word end (जळगांव = जळगाव), so only the latter is dropped.
_OPTIONAL_ANUSVARA = re.compile(r"ं(?=[यरऱलवशषसह]|[^क-ह]|$)")
# OCR artefact: a consonant + virama followed by an independent vowel (भुर्ईमूग).
_STRAY_HALANT = re.compile(r"[क-ह]्(?=[ऄ-औ])")
_TOKEN = re.compile(r"[ऀ-ॣॱ-ॿ]+")

# Links between a stem and an ending: oblique -ा (भाताला), plural -ां (द्राक्षांना), -े (औरंगाबादेत).
_LINKS = ("", "ा", "ां", "े")
_POSTPOSITIONS = (
    "", "ला", "ना", "ले", "स", "त", "मध्ये", "मधे", "मधील", "मधला", "मधली", "मधले", "साठी",
    "करिता", "करीता", "करता", "चा", "ची", "चे", "च्या", "चं", "ने", "नी", "नं", "वर", "वरील",
    "कडे", "कडून", "पासून", "हून", "पर्यंत", "तील", "तला", "तली", "तले", "तल्या", "तून", "बाबत", "कर",
)
_CLITICS = ("", "ही", "च")

_CELL_END = r"([^;|\n]+)"
_DISTRICT_CELL = re.compile(r"जिल्ह(?:ा|्याचे नाव)\s*[:：]\s*" + _CELL_END)
_CROP_CELL = re.compile(r"(?:^|[;|\n])\s*पीक(?:ाचे नाव)?\s*[:：]\s*" + _CELL_END)
_CROP_PREFIX = re.compile(r"^(?:(?:उ|र|ख)\.\s*|(?:उन्हाळी|रब्बी|खरीप)\s+)")
_CROP_SUFFIX = re.compile(r"\s*(?:(?:बा|जि)\.|बागायती?|जिरायती?)$")
_PARENTHETICAL = re.compile(r"\(([^)]*)\)")
_NAME = re.compile(r"^[ऀ-ॣॱ-ॿ]+(?: [ऀ-ॣॱ-ॿ]+){0,2}$")


def fold(text: str) -> str:
    """Merge spelling variants: vowel length, ढ/ड, ऱ/र, ण/न, optional anusvara, nukta, ZWJ."""
    text = unicodedata.normalize("NFC", text)
    text = _STRAY_HALANT.sub("", text)
    text = _OPTIONAL_ANUSVARA.sub("", text)
    return text.translate(_FOLD_MAP)


_SUFFIXES: FrozenSet[str] = frozenset(fold(a + b + c) for a, b, c in product(_LINKS, _POSTPOSITIONS, _CLITICS))


def tokens(text: str) -> List[str]:
    return _TOKEN.findall(fold(text))


def district_cells(text: str) -> List[str]:
    """Values of `जिल्हा:` table context lines and cells."""
    return [m.group(1).strip() for m in _DISTRICT_CELL.finditer(text)]


def crop_cells(text: str) -> List[str]:
    """Values of `पीक:` table cells."""
    return [m.group(1).strip() for m in _CROP_CELL.finditer(text)]


def crop_names_from_label(label: str) -> Tuple[str, ...]:
    """'भात (तांदूळ)' → ('भात', 'तांदूळ'); 'उ. भुईमूग' → ('भुईमूग',); 'गहू बा.' → ('गहू',)."""
    aliases = [a.strip() for a in _PARENTHETICAL.findall(label)]
    main = _CROP_SUFFIX.sub("", _CROP_PREFIX.sub("", _PARENTHETICAL.sub(" ", label).strip())).strip()
    return tuple(n for n in (main, *aliases) if _NAME.match(n))


def _surface_forms(name: str) -> Tuple[Tuple[str, ...], ...]:
    words = tuple(tokens(name))
    if not words:
        return ()
    forms = [words]
    last = words[-1]
    if last.endswith(("ा", "े")) and len(last) > 1:
        forms.append(words[:-1] + (last[:-1] + "्या",))
    return tuple(forms)


@dataclass(frozen=True)
class Found:
    districts: FrozenSet[str]
    crops: FrozenSet[str]


Forms = Tuple[Tuple[Tuple[str, ...], str], ...]


def _compile(groups: Mapping[str, Iterable[str]]) -> Forms:
    """(folded token sequence, canonical name) pairs, longest sequences first."""
    pairs = {(form, canonical) for canonical, names in groups.items()
             for name in (canonical, *names) for form in _surface_forms(name)}
    return tuple(sorted(pairs, key=lambda p: (-len(p[0]), -len(p[0][-1]), p)))


def _token_matches(token: str, form: str) -> bool:
    return token.startswith(form) and token[len(form):] in _SUFFIXES


def _match(words: List[str], forms: Forms) -> FrozenSet[str]:
    found, i = set(), 0
    while i < len(words):
        for form, canonical in forms:
            n = len(form)
            if words[i:i + n - 1] == list(form[:-1]) and i + n <= len(words) and _token_matches(words[i + n - 1], form[-1]):
                found.add(canonical)
                i += n
                break
        else:
            i += 1
    return frozenset(found)


@dataclass(frozen=True)
class EntityLexicon:
    district_forms: Forms
    crop_forms: Forms

    def find(self, text: str) -> Found:
        words = tokens(text)
        return Found(districts=_match(words, self.district_forms), crops=_match(words, self.crop_forms))


def _crop_groups(texts: Iterable[str]) -> Dict[str, Tuple[str, ...]]:
    groups: Dict[str, Tuple[str, ...]] = {c: tuple(a) for c, a in CROPS.items()}
    canonical_by_key = {fold(n): c for c, names in groups.items() for n in (c, *names)}
    for text in texts:
        for label in crop_cells(text):
            names = crop_names_from_label(label)
            if not names:
                continue
            known = next((canonical_by_key[fold(n)] for n in names if fold(n) in canonical_by_key), None)
            canonical = known or names[0]
            new = tuple(n for n in names if fold(n) not in canonical_by_key)
            groups = {**groups, canonical: groups.get(canonical, ()) + new}
            canonical_by_key.update({fold(n): canonical for n in new})
    return groups


def build_lexicon(texts: Iterable[str]) -> EntityLexicon:
    """Static districts + static crops + crop labels found in the given chunk texts."""
    return EntityLexicon(district_forms=_compile(DISTRICTS), crop_forms=_compile(_crop_groups(texts)))
