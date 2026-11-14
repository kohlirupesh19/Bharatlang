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


Mention = Tuple[int, int, str]  # first token, end token (exclusive), canonical name


def _mentions(words: List[str], forms: Forms) -> List[Mention]:
    """Every entity mention, in order of appearance."""
    found: List[Mention] = []
    i = 0
    while i < len(words):
        for form, canonical in forms:
            n = len(form)
            if words[i:i + n - 1] == list(form[:-1]) and i + n <= len(words) and _token_matches(words[i + n - 1], form[-1]):
                found.append((i, i + n, canonical))
                i += n
                break
        else:
            i += 1
    return found


def _match(words: List[str], forms: Forms) -> FrozenSet[str]:
    return frozenset(canonical for _, _, canonical in _mentions(words, forms))


# Words that mark the actual question (standard Marathi and Varhadi), and list conjunctions.
QUESTION_WORDS = ("किती", "कितला", "कितली", "कितले", "कोणत्या", "कोणता", "कोणती", "कोणते",
                  "काय", "कधी", "कुठे", "कसे", "कसा", "कशी", "का")
CONJUNCTIONS = ("आणि", "व", "किंवा", "अन्", "अन", "तसेच")
_QUESTION_WORDS: FrozenSet[str] = frozenset(fold(w) for w in QUESTION_WORDS)
_CONJUNCTIONS: FrozenSet[str] = frozenset(fold(w) for w in CONJUNCTIONS)


# Words after a mention that mark it as backstory, not as what is asked ("ज्वारी आणि तूर घेतो",
# "हरभरा पेरतो", "भात आणि नाचणी होते", "केळीची बाग नाही"). Matched as token prefixes. The
# copula आहे is deliberately absent: "ठाण्यात सोयाबीन आहे आणि नाशिकमध्ये कांदा, हप्ता किती?" asks both.
CROP_BACKSTORY = ("घेतो", "घेतात", "घेतल", "लावतो", "लावतात", "लावल", "लावून", "करतो", "करतात", "केले",
                  "केली", "केला", "पेरतो", "पेरतात", "पेरल", "पेरणार", "पिकवतो", "पिकवतात", "काढल",
                  "होते", "होता", "होती", "नाही", "न्हाई")
DISTRICT_BACKSTORY = ("राहतो", "राहतात", "राहते", "आलो", "आले")
_CROP_BACKSTORY = tuple(fold(w) for w in CROP_BACKSTORY)
# A farming verb also marks the place it follows as backstory ("लातूरला पाहुणे सोयाबीन घेतात").
_DISTRICT_BACKSTORY = tuple(fold(w) for w in DISTRICT_BACKSTORY + CROP_BACKSTORY)
_OF_PLACE = tuple(fold(w) for w in ("चा", "ची", "चे"))  # "मी नाशिकचा आहे": I am from Nashik
_IS = frozenset(fold(w) for w in ("आहे", "हाय"))


def _groups(mentions: List[Mention], words: List[str]) -> List[List[int]]:
    """Mentions listed together: adjacent or joined by one conjunction ("नाशिक, ठाणे आणि पुणे")."""
    groups: List[List[int]] = []
    for i in range(len(mentions)):
        gap = words[mentions[i - 1][1]:mentions[i][0]] if i else ["-"]
        if i and (not gap or (len(gap) == 1 and gap[0] in _CONJUNCTIONS)):
            groups[-1].append(i)
        else:
            groups.append([i])
    return groups


def _is_backstory(group: List[int], mentions: List[Mention], words: List[str],
                  question_words: List[int], cues: Tuple[str, ...], places: bool) -> bool:
    """Does a backstory cue follow the group before the next other entity or question word?"""
    names = {mentions[i][2] for i in group}
    end = mentions[group[-1]][1]
    stops = [m[0] for m in mentions if m[0] >= end and m[2] not in names] + [q for q in question_words if q >= end]
    window = words[end:min(stops, default=len(words))]
    if places and window and window[0] in _IS and words[end - 1].endswith(_OF_PLACE):
        return True
    return any(w.startswith(cues) and _is_statement(end + k, words) for k, w in enumerate(window))


_IF = frozenset(fold(w) for w in ("तर", "तरी"))
_IF_ENDING = fold("ल्यास")  # लावल्यास, केल्यास: "if I plant…"
_YES_NO = fold("का")


def _is_statement(at: int, words: List[str]) -> bool:
    """A cue states backstory unless it asks ("नाही का", "घेतो का") or sets a condition ("केले तर").

    Only the particle directly after the cue counts: without punctuation, "पेरतो. पयशे कितले"
    or "पिकवतो, किती" cannot be told from a question about the crop before it.
    """
    following = words[at + 1] if at + 1 < len(words) else ""
    if words[at].endswith(_IF_ENDING):
        return False
    return following != _YES_NO and following not in _IF


def _asked(mentions: List[Mention], words: List[str], question_words: List[int],
           cues: Tuple[str, ...], places: bool) -> FrozenSet[str]:
    """Mentions a question is about. Only mentions the sentence marks as backstory are left out.

    - no question word: every mention is asked (nothing can be ruled out);
    - the focus is every mention after the last question word ("किती हप्ता आहे ज्वारीचा"), else
      the one nearest before it, with whatever is listed with it ("नाशिक आणि ठाणे"): always asked;
    - any other entity is asked unless a backstory cue follows one of its mentions ("ज्वारी आणि
      तूर घेतो"). Two pairs named before one question ("ठाण्यात सोयाबीन आणि नाशिकमध्ये कांदा …
      किती") are both asked, so a missing one is refused rather than answered with the other's row.
    """
    if not question_words:
        return frozenset(canonical for _, _, canonical in mentions)
    last_q = question_words[-1]
    after = [i for i, m in enumerate(mentions) if m[0] > last_q]
    before = [i for i, m in enumerate(mentions) if m[1] <= last_q]
    focus = set(after or before[-1:])
    groups = _groups(mentions, words)
    asked, backstory = set(), set()
    for group in groups:
        names = {mentions[i][2] for i in group}
        if focus & set(group):
            asked |= names
        elif _is_backstory(group, mentions, words, question_words, cues, places):
            backstory |= names
        else:
            asked |= names
    focus_names = {mentions[i][2] for g in groups if focus & set(g) for i in g}
    return frozenset(focus_names | (asked - backstory))


@dataclass(frozen=True)
class EntityLexicon:
    district_forms: Forms
    crop_forms: Forms

    def find(self, text: str) -> Found:
        """Every district and crop mentioned."""
        words = tokens(text)
        return Found(districts=_match(words, self.district_forms), crops=_match(words, self.crop_forms))

    def find_asked(self, text: str) -> Found:
        """The district(s) and crop(s) the question is about, not those given as context.

        Farmers give context before the question ("…we grow jowar and tur … what is the jowar
        premium?") and ASR output has no punctuation, so sentences cannot be used. The rule
        (`_asked`) errs towards asking: an entity is left out only when the sentence marks it
        as backstory, so a wrongly kept entity can cost a refusal but cannot let a trap through.
        """
        words = tokens(text)
        question_words = [i for i, w in enumerate(words) if w in _QUESTION_WORDS]
        return Found(
            districts=_asked(_mentions(words, self.district_forms), words, question_words, _DISTRICT_BACKSTORY, True),
            crops=_asked(_mentions(words, self.crop_forms), words, question_words, _CROP_BACKSTORY, False))


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
