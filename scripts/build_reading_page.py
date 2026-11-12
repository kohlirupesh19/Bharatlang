"""Build the speaker-facing reading page from the vault note (single source of truth).

usage: python build_reading_page.py <vault .md> <out .html>
"""
import html
import json
import re
import sys
from pathlib import Path

NOISY_REPEAT = {"C02", "C03", "C10"}
GROUPS = [
    ("C", "सर्वांसाठी", "For everyone",
     "प्रत्येक वाचकाने हे बारा परिच्छेद वाचायचे आहेत.", "Every reader reads these twelve paragraphs."),
    ("V", "वऱ्हाडी परिच्छेद", "Varhadi paragraphs",
     "फक्त विदर्भातील वाचकांसाठी (वऱ्हाडी, नागपुरी, झाडीबोली).", "Only for readers from Vidarbha (Varhadi, Nagpuri, Zadiboli)."),
    ("F", "आपल्या शब्दांत", "In your own words",
     "हे वाचायचे नाही. कागद न पाहता आपल्या बोलण्यात सांगा.", "Do not read these out. Say them in your own words without looking."),
]
ACCENTS = [
    ("std", "प्रमाण / Standard (Pune–Mumbai)"), ("varhadi", "वऱ्हाडी / Varhadi"), ("nagpuri", "नागपुरी / Nagpuri"),
    ("zadi", "झाडीबोली / Zadiboli"), ("marathwadi", "मराठवाडी / Marathwadi"), ("khandeshi", "खानदेशी / Khandeshi (Ahirani)"),
    ("konkani", "कोकणी / Konkani-Marathi (Malvani)"), ("deshi", "देशी / Deshi (Kolhapur–Solapur)"), ("other", "इतर / Other"),
]


def parse(md: str):
    section = md.split("\n## Paragraphs\n", 1)[1].split("\n## ", 1)[0]
    items = []
    for block in re.split(r"\n(?=### )", section.strip()):
        head, _, body = block.partition("\n")
        m = re.match(r"### (\w+) · (.+)", head)
        if m:
            lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
            english = [ln[4:] for ln in lines if ln.startswith("EN: ")]
            marathi = [ln for ln in lines if not ln.startswith("EN: ")]
            assert len(english) == 1, f"{m.group(1)}: expected one EN: line"
            items.append({"id": m.group(1), "labels": [s.strip() for s in m.group(2).split("·")],
                          "text": " ".join(marathi), "en": english[0]})
    return items


def card(item) -> str:
    tags = "".join(f'<span class="tag">{html.escape(t)}</span>' for t in item["labels"])
    noisy = '<span class="tag tag-noisy">गोंगाटातही पुन्हा · also noisy</span>' if item["id"] in NOISY_REPEAT else ""
    free = item["id"].startswith("F")
    return f"""
<article class="card{' card-free' if free else ''}" id="{item['id']}">
  <header class="card-head">
    <span class="pid">{item['id']}</span>
    <div class="tags">{tags}{noisy}</div>
  </header>
  <div class="texts">
    <p class="reading text-mr read-big" lang="mr" data-gloss="मराठी">{html.escape(item['text'])}</p>
    <p class="reading text-en read-small" lang="en" data-gloss="English meaning">{html.escape(item['en'])}</p>
  </div>
  <div class="fname-row">
    <code class="fname" data-item="{item['id']}">spk__</code>
    <button type="button" class="copy" data-item="{item['id']}" aria-label="Copy file name for {item['id']}">कॉपी · Copy</button>
  </div>
</article>"""


def build(items) -> str:
    sections = []
    for prefix, title, title_en, note, note_en in GROUPS:
        group = [i for i in items if i["id"].startswith(prefix)]
        draft = ('<p class="draft">मसुदा: हे परिच्छेद रेकॉर्डिंगपूर्वी एखाद्या स्थानिक वऱ्हाडी व्यक्तीने तपासायचे आहेत. '
                 'काही शब्द अनैसर्गिक वाटले तर रेकॉर्ड करणाऱ्याला आधी सांगा.'
                 '<span class="en-line">Draft: a native Varhadi speaker should check these before recording. '
                 'If any word sounds unnatural, tell the recorder first.</span></p>') if prefix == "V" else ""
        sections.append(f"""
<section class="group" id="set-{prefix}">
  <h2>{title} <span class="h-en">{title_en}</span> <span class="count">{len(group)}</span></h2>
  <p class="group-note">{note}<span class="en-line">{note_en}</span></p>{draft}
  <div class="cards">{''.join(card(i) for i in group)}</div>
</section>""")
    options = "".join(f'<option value="{c}">{html.escape(n)}</option>' for c, n in ACCENTS)
    template = Path(__file__).with_name("reading_page_template.html").read_text(encoding="utf-8")
    return (template.replace("{{ACCENT_OPTIONS}}", options)
                    .replace("{{SECTIONS}}", "".join(sections))
                    .replace("{{ITEM_IDS}}", json.dumps([i["id"] for i in items])))


if __name__ == "__main__":
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    items = parse(src.read_text(encoding="utf-8"))
    assert len(items) == 21, f"expected 21 items, found {len(items)}"
    out.write_text(build(items), encoding="utf-8")
    print(f"wrote {out} with {len(items)} items")
