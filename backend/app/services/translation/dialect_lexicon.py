"""
Single source of truth for Varhadi dialect data: word lists, rule tables and the
government terminology glossary. Logic lives in normalization.py.

Entries are split by how much they prove about dialect:
- VARHADI_STRONG_MARKERS: forms that standard Marathi does not use. Evidence of Varhadi.
- COLLOQUIAL_NORMALIZATIONS: informal spellings heard across Maharashtra. They are
  rewritten for better retrieval but are NOT evidence of Varhadi.
"""
from typing import Dict, FrozenSet

VARHADI_STRONG_MARKERS: Dict[str, str] = {
    # Pronouns & dative markers (-ले for standard -ला)
    "मले": "मला",
    "म्हाले": "मला",
    "तुले": "तुला",
    "त्याले": "त्याला",
    "ह्याले": "याला",
    "आम्हाले": "आम्हाला",
    "आमाले": "आम्हाला",
    "तुम्हाले": "तुम्हाला",
    "तुमाले": "तुम्हाला",
    "कोणाले": "कोणाला",
    "त्यायले": "त्यांना",

    # Interrogatives & adverbs
    "काऊन": "का",
    "कायले": "कशासाठी",
    "कठे": "कोठे",
    "कवा": "केव्हा",
    "कस्तं": "कसे",

    # Verbs & auxiliaries
    "व्हय": "आहे",
    "न्हाई": "नाही",
    "नोको": "नको",
    "व्हता": "होता",
    "व्हती": "होती",
    "व्हतं": "होते",
    "व्हते": "होते",
    "व्हाया": "व्हायला",
    "पायजे": "पाहिजे",
    "पाह्यजे": "पाहिजे",
    "मिळन": "मिळेल",
    "लागन": "लागेल",
    "गेलतो": "गेलो होतो",
    "गेलता": "गेला होता",
    # Short infinitives that the generic suffix rules would get wrong
    "द्याले": "द्यायला",
    "घ्याले": "घ्यायला",
    "न्याले": "न्यायला",

    # Quantifiers & demonstratives
    "इतलं": "इतके",
    "तितलं": "तितके",
    "कितलं": "किती",

    # Farming & administrative terms
    "कागदपत्तुर": "कागदपत्रे",
    "पयशे": "पैसे",
    "वावर": "शेत",
    "साताबारा": "७/१२ उतारा",
}

COLLOQUIAL_NORMALIZATIONS: Dict[str, str] = {
    "नाय": "नाही",
    "हाय": "आहे",
    "कसं": "कसे",
    "कुठं": "कुठे",
    "खातं": "खाते",
    "कागद": "कागदपत्रे",
    "नुकसानी": "नुकसान",
    "सातबारा": "७/१२ उतारा",
    "आठा": "८-अ उतारा",
}

# Combined view kept for callers that only need "is this word rewritten, and to what".
VARHADI_TO_STANDARD_MARATHI: Dict[str, str] = {
    **COLLOQUIAL_NORMALIZATIONS,
    **VARHADI_STRONG_MARKERS,
}

# --- Rule tables -----------------------------------------------------------

# Varhadi infinitive "<stem>ाले" = standard "<stem>ायला" (कराले -> करायला).
# Restricted to known verb stems because standard past-tense verbs also end in
# -ाले (झाले, आले, मिळाले) and must not be touched.
INFINITIVE_VERB_STEMS: FrozenSet[str] = frozenset({
    "कर", "भर", "सांग", "विचार", "पाठव", "काढ", "बघ", "पाह", "लिह",
    "मिळव", "दाखव", "जोड", "बदल", "वाप", "आण", "ठेव",
})

# Varhadi obligation "<verb>ा लागते" = standard "<verb>ावे लागते" (करा लागते -> करावे लागते).
# Restricted to verbs: nouns ending in -ा also precede लागते (दाखला लागतो = a certificate is needed).
OBLIGATION_VERB_FORMS: Dict[str, str] = {
    "करा": "करावे",
    "भरा": "भरावे",
    "द्या": "द्यावे",
    "घ्या": "घ्यावे",
    "जा": "जावे",
    "सांगा": "सांगावे",
    "काढा": "काढावे",
    "लिहा": "लिहावे",
    "आणा": "आणावे",
    "जोडा": "जोडावे",
}
OBLIGATION_AUXILIARY_STEM = "लाग"

# Standard words ending in -्याले that are NOT Varhadi datives.
DATIVE_RULE_EXCEPTIONS: FrozenSet[str] = frozenset({"प्याले", "भ्याले", "व्याले"})

# Colloquial "भेटणे" used for "to receive" = standard "मिळणे". Only these verb endings
# are rewritten so the noun भेट (visit, gift) and its compounds stay intact.
RECEIVE_STEM_COLLOQUIAL = "भेट"
RECEIVE_STEM_STANDARD = "मिळ"
RECEIVE_ENDINGS: Dict[str, str] = {
    "तील": "तील",
    "तात": "तात",
    "ते": "ते",
    "तो": "तो",
    "तं": "ते",
    "त": "त",
    "णार": "णार",
    "ेल": "ेल",
    "न": "ेल",
    "ला": "ाला",
    "ली": "ाली",
    "ले": "ाले",
    "लं": "ाले",
    "ाले": "ायला",
    "ायले": "ायला",
    "ायला": "ायला",
}

# --- Glossary --------------------------------------------------------------

# Marathi-English Government & Agricultural Terminology Glossary
GLOSSARY_MARATHI_ENGLISH: Dict[str, str] = {
    "शेतकरी कर्जमाफी": "Farmer Loan Waiver",
    "कर्जमाफी": "Loan Waiver",
    "पीक विमा": "Crop Insurance",
    "पंतप्रधान पीक विमा योजना": "Pradhan Mantri Fasal Bima Yojana (PMFBY)",
    "शासकीय अनुदान": "Government Subsidy",
    "अनुदान": "Subsidy / Grant",
    "नमो शेतकरी महासन्मान निधी": "Namo Shetkari Mahasanman Nidhi",
    "पीएम किसान": "PM-KISAN Samman Nidhi",
    "सातबारा उतारा": "7/12 Land Record (Record of Rights)",
    "८-अ उतारा": "8-A Land Extract",
    "आधार संलग्न बँक खाते": "Aadhaar-seeded Bank Account",
    "थेट लाभ हस्तांतरण": "Direct Benefit Transfer (DBT)",
    "महाडीबीटी": "MahaDBT Portal",
    "पात्रता निकष": "Eligibility Criteria",
    "आवश्यक कागदपत्रे": "Required Documents",
    "अर्ज प्रक्रिया": "Application Procedure",
    "अतिवृष्टी नुकसान भरपाई": "Excess Rainfall Damage Compensation",
    "ठिबक सिंचन अनुदान": "Drip Irrigation Subsidy",
    "तुषार सिंचन": "Sprinkler Irrigation",
    "कृषी पंप वीज जोडणी": "Agricultural Pump Electricity Connection",
    "गोपीनाथ मुंडे शेतकरी अपघात सुरक्षा सानुग्रह अनुदान": "Gopinath Munde Farmer Accident Insurance Scheme",
    "तालुका कृषी अधिकारी": "Taluka Agriculture Officer",
    "ग्रामसेवक": "Gram Sevak / Village Officer",
    "तलाठी": "Talathi / Revenue Officer"
}
