"""Score read-aloud clips end to end: meaning kept, answer correct, WER (diagnostic).

  # on the laptop (the vault is there): extract the paragraph texts once
  python scripts/score_readaloud.py refs --note C:/dev/second_brain/bharatlang/docs/eval/multi_speaker_read_aloud.md --out refs.json
  # on the office box, with the stack running
  python scripts/score_readaloud.py score --wav-dir eval_data/local/<speaker>/wav --refs refs.json --out scores.json [--item 1.wav=C04 ...]

Each clip goes through /api/chat/voice exactly as the app's microphone would send it. Without
--item, a clip's paragraph is the one its transcript is closest to (strict WER).
"""
import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.evaluation.readaloud import (  # noqa: E402
    ITEMS, answer_check, loose_word_errors, meaning_check, parse_paragraphs,
)


def cmd_refs(args: argparse.Namespace) -> None:
    refs = parse_paragraphs(Path(args.note).read_text(encoding="utf-8"))
    Path(args.out).write_text(json.dumps(refs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(refs)} paragraphs -> {args.out}")


def _self_check(refs: Dict[str, str], lexicon) -> None:
    """Each reference paragraph must pass its own meaning check, or the spec is wrong."""
    bad = {item: meaning_check(text, ITEMS[item], lexicon) for item, text in refs.items() if item in ITEMS}
    bad = {item: r for item, r in bad.items() if not r.kept}
    if bad:
        raise SystemExit(f"Spec/paragraph mismatch, fix ITEMS first: {bad}")


def _closest_item(transcript: str, refs: Dict[str, str]) -> str:
    rates = {item: loose_word_errors(text, transcript)[0] / max(1, loose_word_errors(text, transcript)[2])
             for item, text in refs.items() if item in ITEMS}
    return min(rates, key=rates.get)


def _ask(api: str, wav: Path) -> dict:
    with wav.open("rb") as fh:
        response = httpx.post(f"{api}/api/chat/voice", files={"audio": (wav.name, fh, "audio/wav")},
                              data={"language": "mr", "voice_output": "false"}, timeout=600)
    response.raise_for_status()
    return response.json()


def cmd_score(args: argparse.Namespace) -> None:
    from backend.app.services.rag.evidence_index import current_evidence_index
    lexicon = current_evidence_index().lexicon
    refs = json.loads(Path(args.refs).read_text(encoding="utf-8"))
    _self_check(refs, lexicon)
    fixed = dict(pair.split("=", 1) for pair in args.item)

    rows: List[dict] = []
    for wav in sorted(Path(args.wav_dir).glob("*.wav")):
        reply = _ask(args.api, wav)
        transcript = reply["recognized_text"]
        item = fixed.get(wav.name) or _closest_item(transcript, refs)
        strict, loose, words = loose_word_errors(refs[item], transcript)
        meaning = meaning_check(transcript, ITEMS[item], lexicon)
        answer = answer_check(reply["answer"], ITEMS[item])
        rows.append({"clip": wav.name, "item": item, "words": words, "strict_errors": strict, "loose_errors": loose,
                     "meaning_kept": meaning.kept, "meaning": asdict(meaning),
                     "answer_correct": answer.correct, "answer_check": asdict(answer),
                     "transcript": transcript, "answer": reply["answer"],
                     "abstention_reason": reply.get("abstention_reason"),
                     "unverified_numbers": reply.get("unverified_numbers"),
                     "answer_language": reply.get("answer_language"), "latency_ms": reply.get("latency_ms")})
        _print_row(rows[-1])
    _print_summary(rows)
    Path(args.out).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


def _print_row(r: dict) -> None:
    m, a = r["meaning"], r["answer_check"]
    print(f"{r['clip']} {r['item']}: meaning {'OK' if r['meaning_kept'] else 'LOST'}"
          f" (district {m['heard_districts']}, crop {m['heard_crops']}, missing {list(m['missing_phrases'])})"
          f" | answer {'OK' if r['answer_correct'] else 'WRONG'}"
          f" (refused={a['refused']}, missing {list(a['missing_gold'])})"
          f" | WER strict {r['strict_errors'] / r['words']:.1%} loose {r['loose_errors'] / r['words']:.1%}")


def _print_summary(rows: List[dict]) -> None:
    n, words = len(rows), sum(r["words"] for r in rows) or 1
    print(f"SUMMARY {n} clips: meaning kept {sum(r['meaning_kept'] for r in rows)}/{n}, "
          f"answer correct {sum(r['answer_correct'] for r in rows)}/{n}, "
          f"WER strict {sum(r['strict_errors'] for r in rows) / words:.1%}, "
          f"loose {sum(r['loose_errors'] for r in rows) / words:.1%} over {words} words")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    refs = sub.add_parser("refs", help="extract paragraph texts from the vault note")
    refs.add_argument("--note", required=True)
    refs.add_argument("--out", required=True)
    score = sub.add_parser("score", help="score clips through the running app")
    score.add_argument("--wav-dir", required=True)
    score.add_argument("--refs", required=True)
    score.add_argument("--out", required=True)
    score.add_argument("--api", default="http://127.0.0.1:8000")
    score.add_argument("--item", action="append", default=[], help="clip=ITEM, e.g. 1.wav=C04 (repeatable)")
    args = parser.parse_args()
    {"refs": cmd_refs, "score": cmd_score}[args.command](args)


if __name__ == "__main__":
    main()
