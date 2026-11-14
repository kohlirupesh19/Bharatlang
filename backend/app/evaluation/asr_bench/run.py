"""CLI: benchmark an ASR candidate, or compare two finished runs.

  python -m backend.app.evaluation.asr_bench.run bench --dataset respin --model small
  python -m backend.app.evaluation.asr_bench.run compare RUN_A RUN_B
"""
import argparse
import json
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from backend.app.evaluation.asr_bench.datasets import DATASETS, EVAL_ROOT, dataset_revision, iter_samples
from backend.app.evaluation.asr_bench.engines import FasterWhisperCandidate
from backend.app.evaluation.asr_bench.normalize import NORMALIZER_VERSION, normalize_marathi
from backend.app.evaluation.asr_bench.stats import (
    UtteranceScore, paired_bootstrap, score_utterance, speaker_bootstrap_ci,
)

RUNS_DIR = EVAL_ROOT / "runs"


def gpu_memory_mib() -> int:
    """Total dedicated memory in use on GPU 0 (all processes), or -1 if unavailable."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, check=True, timeout=10)
        return int(out.stdout.strip().splitlines()[0])
    except (OSError, subprocess.SubprocessError, ValueError):
        return -1


def summarize(scores: List[UtteranceScore], dialect_of: Dict[str, str]) -> Dict[str, object]:
    by_dialect: Dict[str, List[UtteranceScore]] = defaultdict(list)
    for s in scores:
        by_dialect[dialect_of[s.utt_id]].append(s)
    result = {"overall": speaker_bootstrap_ci(scores)}
    if len(by_dialect) > 1:
        result["by_dialect"] = {d: speaker_bootstrap_ci(v) for d, v in sorted(by_dialect.items())}
    return result


def bench(args: argparse.Namespace) -> Path:
    candidate = FasterWhisperCandidate(args.model, args.device, args.compute_type, args.beam)
    run_id = f"{datetime.now():%Y%m%d-%H%M%S}_{args.dataset}_{Path(args.model).name}_{args.device}"
    out_dir = RUNS_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=False)

    vram_before = gpu_memory_mib()
    t_load = time.perf_counter()
    candidate.load()
    load_sec = time.perf_counter() - t_load
    vram_loaded = gpu_memory_mib()

    scores: List[UtteranceScore] = []
    dialect_of: Dict[str, str] = {}
    audio_sec = decode_sec = 0.0
    with (out_dir / "utterances.jsonl").open("w", encoding="utf-8") as fh:
        for i, sample in enumerate(iter_samples(args.dataset, args.dialect, args.limit), start=1):
            t0 = time.perf_counter()
            hyp_raw = candidate.transcribe(sample.audio)
            elapsed = time.perf_counter() - t0
            decode_sec += elapsed
            audio_sec += sample.duration
            ref, hyp = normalize_marathi(sample.reference), normalize_marathi(hyp_raw)
            score = score_utterance(sample.utt_id, sample.speaker, ref, hyp)
            scores.append(score)
            dialect_of[sample.utt_id] = sample.dialect
            fh.write(json.dumps({"utt_id": sample.utt_id, "speaker": sample.speaker, "dialect": sample.dialect,
                                 "duration": sample.duration, "ref": ref, "hyp": hyp, "hyp_raw": hyp_raw,
                                 "word_errors": score.word_errors, "ref_words": score.ref_words,
                                 "char_errors": score.char_errors, "ref_chars": score.ref_chars,
                                 "decode_sec": round(elapsed, 4)}, ensure_ascii=False) + "\n")
            if i % 100 == 0:
                print(f"  {i} utterances, RTF {decode_sec / audio_sec:.3f}", flush=True)
    if not scores:
        raise RuntimeError("No samples were scored; check --dataset/--dialect/--limit")

    summary = {
        "run_id": run_id, "created_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": args.dataset, "dataset_revision": dataset_revision(args.dataset),
        "bootstrap_unit": DATASETS[args.dataset].bootstrap_unit, "dialect_filter": args.dialect,
        "limit": args.limit, "normalizer": NORMALIZER_VERSION, "candidate": candidate.settings(),
        "timing": {"load_sec": round(load_sec, 2), "audio_sec": round(audio_sec, 1),
                   "decode_sec": round(decode_sec, 1), "rtf": round(decode_sec / audio_sec, 4)},
        "gpu_mib": {"before_load": vram_before, "after_load": vram_loaded, "after_run": gpu_memory_mib()},
        "metrics": summarize(scores, dialect_of),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"run_id": run_id, "timing": summary["timing"], "metrics": summary["metrics"]}, indent=2))
    return out_dir


def _load_scores(run_dir: Path) -> List[UtteranceScore]:
    rows = [json.loads(line) for line in (run_dir / "utterances.jsonl").read_text(encoding="utf-8").splitlines()]
    return [UtteranceScore(r["utt_id"], r["speaker"], r["ref_words"], r["word_errors"],
                           r["ref_chars"], r["char_errors"]) for r in rows]


def compare(args: argparse.Namespace) -> None:
    base_dir, cand_dir = RUNS_DIR / args.baseline, RUNS_DIR / args.candidate
    for d in (base_dir, cand_dir):
        if not (d / "utterances.jsonl").exists():
            raise FileNotFoundError(f"Run not found: {d}")
    result = paired_bootstrap(_load_scores(base_dir), _load_scores(cand_dir))
    print(json.dumps({"baseline": args.baseline, "candidate": args.candidate, **result}, indent=2))


def main(argv: List[str]) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("bench")
    b.add_argument("--dataset", choices=sorted(DATASETS), required=True)
    b.add_argument("--dialect", action="append", choices=["D1", "D2", "D3", "D4"])
    b.add_argument("--limit", type=int)
    b.add_argument("--model", default="small")
    b.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    b.add_argument("--compute-type", default="int8_float16")
    b.add_argument("--beam", type=int, default=5)
    c = sub.add_parser("compare")
    c.add_argument("baseline")
    c.add_argument("candidate")
    args = parser.parse_args(argv)
    if getattr(args, "limit", None) is not None and args.limit < 1:
        parser.error("--limit must be >= 1")
    if getattr(args, "beam", 1) < 1:
        parser.error("--beam must be >= 1")
    bench(args) if args.command == "bench" else compare(args)


if __name__ == "__main__":
    main(sys.argv[1:])
