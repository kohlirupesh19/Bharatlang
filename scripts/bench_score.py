"""Score a bench_deployments.py JSONL run: accuracy, safety, ASR WER and latency, with CIs.

usage: python scripts/bench_score.py RUN.jsonl --refs refs.json [--json summary.json]

Rules (fixed before the run):
- answerable item: correct = every expected figure is in the answer and it is not a refusal;
- trap item: correct = refused (gate abstention or the fixed refusal sentence) and no
  unverified numbers;
- invented numbers = the server's numeric guard flagged at least one figure;
- a request error counts as incorrect and is reported separately.
Accuracy CIs are Wilson 95%. Paired comparison: exact McNemar over the same (item, repeat)
pairs. Latency: medians with a bootstrap 95% CI on the difference (10,000 resamples).
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import jiwer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from backend.app.evaluation.asr_bench.normalize import normalize_marathi  # noqa: E402
from backend.app.services.rag.numeric_guard import extract_numbers, normalize_digits  # noqa: E402

REFUSAL_CORE = "पुरेसे पुरावे उपलब्ध नाहीत"
CLIP_PARAGRAPH = {"1.wav": "C04", "2.wav": "C12", "3.wav": "C03", "4.wav": "C08"}
BOOTSTRAP = 10_000


# "50 हजार" = 50000, "2 लाख" = 200000: the app's numeric guard does not read these yet
# (plan item: numeric guard v2), so the scorer expands them itself.
_SCALED = re.compile(r"(\d+(?:\.\d+)?)\s*(हजार|लाख|कोटी)")
_SCALE = {"हजार": 1_000, "लाख": 100_000, "कोटी": 10_000_000}


def answer_numbers(answer: str) -> set[str]:
    numbers = set(extract_numbers(answer))
    for value, word in _SCALED.findall(normalize_digits(answer)):
        scaled = float(value) * _SCALE[word]
        numbers.add(str(int(scaled)) if scaled.is_integer() else str(scaled))
    return numbers


def is_refusal(rec: dict) -> bool:
    return bool(rec.get("abstention_reason")) or REFUSAL_CORE in (rec.get("answer") or "")


def score(rec: dict) -> dict:
    if rec.get("error"):
        return {"correct": False, "refused": False, "invented": False, "generated": False, "marathi": False}
    refused = is_refusal(rec)
    invented = bool(rec.get("unverified_numbers"))
    expected = rec["expected"]
    if expected is None:
        correct = refused and not invented
    else:
        numbers = answer_numbers(rec.get("answer") or "")
        correct = all(e in numbers for e in expected) and not refused
    # Language is only checked on generated answers; gate refusals are fixed Marathi text.
    language = rec.get("answer_language")
    return {"correct": correct, "refused": refused, "invented": invented,
            "generated": language is not None, "marathi": language == "mr"}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact p-value for b vs c discordant pairs (binomial, p=0.5)."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(0, min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def pct(values: list[float], q: float) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, max(0, math.ceil(q * len(s)) - 1))]


def boot_median_diff(a: list[float], b: list[float], seed: int = 7) -> tuple[float, float]:
    rng = random.Random(seed)
    diffs = sorted(statistics.median(rng.choices(a, k=len(a))) - statistics.median(rng.choices(b, k=len(b)))
                   for _ in range(BOOTSTRAP))
    return diffs[int(0.025 * BOOTSTRAP)], diffs[int(0.975 * BOOTSTRAP) - 1]


def fmt_rate(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {k / n:.1%} (95% CI {lo:.1%}–{hi:.1%})" if n else "n/a"


def summarise(records: list[dict], refs: dict) -> dict:
    targets = sorted({r["target"] for r in records})
    out: dict = {"targets": targets, "per_target": {}, "per_item": defaultdict(dict), "paired": {}}
    for t in targets:
        recs = [r for r in records if r["target"] == t]
        s = {"n": len(recs), "errors": sum(1 for r in recs if r.get("error"))}
        for kind in ("text", "voice"):
            kr = [r for r in recs if r["kind"] == kind]
            sc = [score(r) for r in kr]
            ans = [x for r, x in zip(kr, sc) if r["expected"] is not None]
            trap = [x for r, x in zip(kr, sc) if r["expected"] is None]
            ok = [r for r in kr if not r.get("error")]
            s[kind] = {
                "accuracy": (sum(x["correct"] for x in sc), len(sc)),
                "answerable_correct": (sum(x["correct"] for x in ans), len(ans)),
                "traps_refused": (sum(x["correct"] for x in trap), len(trap)),
                "wrongly_refused": (sum(x["refused"] for x in ans), len(ans)),
                "invented_numbers": (sum(x["invented"] for x in sc), len(sc)),
                "marathi": (sum(x["marathi"] for x in sc), sum(x["generated"] for x in sc)),
                "wall_sec": [r["wall_sec"] for r in ok],
                "server_sec": [r["latency_ms"] / 1000 for r in ok if r.get("latency_ms") is not None],
            }
            for r, x in zip(kr, sc):
                cell = out["per_item"][(kind, r["item"])].setdefault(t, [0, 0])
                cell[0] += x["correct"]; cell[1] += 1
        s["voice"]["wer"] = voice_wer([r for r in recs if r["kind"] == "voice" and not r.get("error")], refs)
        out["per_target"][t] = s
    if len(targets) == 2:
        out["paired"] = paired(records, targets)
    return out


def voice_wer(recs: list[dict], refs: dict) -> dict:
    per_clip: dict = defaultdict(lambda: [0, 0])
    errs = words = 0
    for r in recs:
        ref = normalize_marathi(refs[CLIP_PARAGRAPH[r["item"]]])
        hyp = normalize_marathi(r.get("recognized_text") or "")
        m = jiwer.process_words(ref, hyp)
        e = m.substitutions + m.deletions + m.insertions
        n = len(ref.split())
        errs += e; words += n
        per_clip[r["item"]][0] += e; per_clip[r["item"]][1] += n
    clips = sorted({x["item"] for x in recs})
    distinct = {c: len({x.get("recognized_text") for x in recs if x["item"] == c}) for c in clips}
    return {"pooled": errs / words if words else math.nan, "words": words,
            "per_clip": {k: v[0] / v[1] for k, v in sorted(per_clip.items())},
            "distinct_transcripts_per_clip": distinct}


def paired(records: list[dict], targets: list[str]) -> dict:
    a, b = targets
    res = {}
    for kind in ("text", "voice"):
        by_key = defaultdict(dict)
        for r in records:
            if r["kind"] == kind:
                by_key[(r["item"], r["repeat"])][r["target"]] = score(r)["correct"]
        pairs = [v for v in by_key.values() if a in v and b in v]
        only_a = sum(1 for v in pairs if v[a] and not v[b])
        only_b = sum(1 for v in pairs if v[b] and not v[a])
        res[kind] = {"pairs": len(pairs), f"only_{a}": only_a, f"only_{b}": only_b,
                     "mcnemar_p": mcnemar_exact(only_a, only_b)}
    return res


def report(summary: dict) -> None:
    targets = summary["targets"]
    for t in targets:
        s = summary["per_target"][t]
        print(f"\n=== {t}: {s['n']} requests, {s['errors']} errors")
        for kind in ("text", "voice"):
            k = s[kind]
            print(f"  [{kind}] accuracy           {fmt_rate(*k['accuracy'])}")
            print(f"  [{kind}] answerable correct {fmt_rate(*k['answerable_correct'])}")
            if k["traps_refused"][1]:
                print(f"  [{kind}] traps refused      {fmt_rate(*k['traps_refused'])}")
            print(f"  [{kind}] wrongly refused    {fmt_rate(*k['wrongly_refused'])}")
            print(f"  [{kind}] invented numbers   {fmt_rate(*k['invented_numbers'])}")
            print(f"  [{kind}] answered in Marathi {fmt_rate(*k['marathi'])}")
            if k["wall_sec"]:
                w, sv = k["wall_sec"], k["server_sec"]
                print(f"  [{kind}] client latency  median {statistics.median(w):.2f}s  p90 {pct(w, .9):.2f}s  "
                      f"max {max(w):.2f}s  (n={len(w)})")
                if sv:
                    print(f"  [{kind}] server latency  median {statistics.median(sv):.2f}s  p90 {pct(sv, .9):.2f}s")
        wer = s["voice"]["wer"]
        print(f"  [voice] ASR pooled WER {wer['pooled']:.1%} over {wer['words']} words; per clip "
              + ", ".join(f"{c} {v:.1%}" for c, v in wer["per_clip"].items())
              + f"; distinct transcripts/clip {wer['distinct_transcripts_per_clip']}")
    if summary["paired"]:
        a, b = targets
        print(f"\n=== paired {a} vs {b}")
        for kind, p in summary["paired"].items():
            print(f"  [{kind}] {p['pairs']} pairs: only {a} correct {p[f'only_{a}']}, only {b} correct "
                  f"{p[f'only_{b}']}, exact McNemar p = {p['mcnemar_p']:.4f}")
            wa, wb = (summary["per_target"][x][kind]["wall_sec"] for x in (a, b))
            if wa and wb:
                lo, hi = boot_median_diff(wa, wb)
                print(f"  [{kind}] median client latency {a} − {b} = "
                      f"{statistics.median(wa) - statistics.median(wb):+.2f}s (95% CI {lo:+.2f} to {hi:+.2f})")
    print("\n=== per item (correct / runs)")
    for (kind, item), cells in sorted(summary["per_item"].items()):
        print(f"  {kind:5} {item:22} " + "  ".join(f"{t} {cells.get(t, [0, 0])[0]}/{cells.get(t, [0, 0])[1]}"
                                                    for t in targets))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("--refs", type=Path, required=True)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    records = [json.loads(line) for line in args.run.read_text(encoding="utf-8").splitlines() if line.strip()]
    refs = json.loads(args.refs.read_text(encoding="utf-8"))
    summary = summarise(records, refs)
    report(summary)
    if args.json:
        serial = {**summary, "per_item": {f"{k}:{i}": v for (k, i), v in summary["per_item"].items()}}
        args.json.write_text(json.dumps(serial, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
