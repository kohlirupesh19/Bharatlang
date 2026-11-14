"""Repeated end-to-end benchmark of two deployments through their public API.

Every request goes through the full pipeline (/api/chat, /api/chat/voice) exactly as a
citizen's would, from the same client, so the numbers are the user-perceived ones.

usage:
  python scripts/bench_deployments.py --repeats 10 --clips <dir with 1-4.wav + refs.json> \
      --target office=http://127.0.0.1:18000 \
      --target aws=https://bharatlang.ideasfreshly.store@~/.bharatlang/site-login.txt \
      --out eval_data/runs/<ts>_deploy_bench.jsonl

A target is NAME=URL or NAME=URL@LOGIN_FILE (basic auth; "user:" and "password:" lines).
Targets run in parallel threads; within a target, requests are strictly sequential, and
each repeat visits the items in a fresh seeded order. One warm-up request per target is
sent first and discarded. Each record is appended to the JSONL as soon as it completes,
so an interrupted run keeps what it measured. Score with scripts/bench_score.py.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

sys.stdout.reconfigure(encoding="utf-8")

# Text items: the 12 graded questions from the 2026-11-12 bake-off (logs/llm_compare.py on
# office). Figures were checked against the GR rate tables (premium = SI x rate).
# expected = ASCII figures a correct answer must all contain; None = must be refused.
TEXT_ITEMS = [
    ("ratnagiri-rice-si", "रत्नागिरी जिल्ह्यात खरीप २०२५ मध्ये भात पिकासाठी विमा संरक्षित रक्कम प्रति हेक्टर किती आहे?", ["61000"]),
    ("nashik-soy-farmer", "नाशिक जिल्ह्यात खरीप २०२५ मध्ये सोयाबीनसाठी शेतकऱ्याला प्रति हेक्टर किती विमा हप्ता भरावा लागेल?", ["817.5"]),
    ("gadchiroli-cotton-si", "गडचिरोली जिल्ह्यात खरीप २०२५ साठी कापूस पिकाची विमा संरक्षित रक्कम किती?", ["59000"]),
    ("dhule-rice-si", "धुळे जिल्ह्यात खरीप २०२५ मध्ये भाताची विमा संरक्षित रक्कम किती आहे?", ["49000"]),
    ("karj-incentive-max", "कर्जमुक्ती योजनेत नियमित कर्ज फेडणाऱ्या शेतकऱ्यांना जास्तीत जास्त किती प्रोत्साहनपर लाभ मिळतो?", ["50000"]),
    ("karj-incentive-years", "प्रोत्साहनपर लाभासाठी कोणत्या आर्थिक वर्षांचा विचार केला जातो?", ["2017", "2018", "2019"]),
    ("varhadi-incentive", "मले कर्ज वेळेवर फेडल्याबद्दल प्रोत्साहन किती भेटन?", ["50000"]),
    ("nashik-cotton-si", "नाशिक जिल्ह्यात खरीप २०२५ साठी कापूस पिकाची विमा संरक्षित रक्कम किती?", ["60000"]),
    ("trap-thane-soy", "ठाणे जिल्ह्यात खरीप २०२५ मध्ये सोयाबीन पिकासाठी शेतकऱ्याला किती विमा हप्ता भरावा लागेल?", None),
    ("trap-mumbai-rice", "मुंबई उपनगर जिल्ह्यात खरीप २०२५ मध्ये भात पिकाची विमा संरक्षित रक्कम किती आहे?", None),
    ("trap-ratnagiri-soy", "रत्नागिरी जिल्ह्यात खरीप २०२५ मध्ये सोयाबीन पिकासाठी विमा संरक्षित रक्कम किती आहे?", None),
    ("trap-solar-pump", "मागेल त्याला सौर कृषी पंप योजनेत किती अनुदान मिळते?", None),
]

# Voice items: the 4 read-aloud clips (spk02, quiet room); clip -> paragraph from the
# 2026-11-12 matching (runner-ups 86-98% WER). Gold = every figure the question asks for.
VOICE_ITEMS = [
    ("1.wav", "C04", ["59000"]),            # Gadchiroli cotton sum insured
    ("2.wav", "C12", ["2000"]),             # Namo instalment amount
    ("3.wav", "C03", ["817.5"]),            # Nashik soybean farmer premium
    ("4.wav", "C08", ["28175", "70.44"]),   # Solapur jowar sum insured and premium
]

WARMUP_QUERY = "नमो शेतकरी महासन्मान निधी योजनेत किती रक्कम मिळते?"
TIMEOUT_SEC = 600


@dataclass(frozen=True)
class Target:
    name: str
    url: str
    auth: Optional[tuple[str, str]]


def parse_target(spec: str) -> Target:
    name, _, rest = spec.partition("=")
    if not name or not rest.startswith(("http://", "https://")):
        raise argparse.ArgumentTypeError(f"bad --target {spec!r}; expected NAME=URL[@LOGIN_FILE]")
    url, _, login = rest.partition("@")
    auth = read_login(Path(login).expanduser()) if login else None
    return Target(name, url.rstrip("/"), auth)


def read_login(path: Path) -> tuple[str, str]:
    fields = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip().lower()] = value.strip()
    user = next((v for k, v in fields.items() if k.startswith("user")), None)
    password = next((v for k, v in fields.items() if k.startswith("pass")), None)
    if not user or not password:
        raise SystemExit(f"{path}: needs 'user:' and 'password:' lines")
    return user, password


def ask_text(client: httpx.Client, query: str) -> dict:
    r = client.post("/api/chat", json={"query": query, "language": "mr", "voice_output": False})
    r.raise_for_status()
    return r.json()


def ask_voice(client: httpx.Client, wav: Path) -> dict:
    with open(wav, "rb") as fh:
        r = client.post("/api/chat/voice", files={"audio": (wav.name, fh, "audio/wav")},
                        data={"language": "mr", "voice_output": "false"})
    r.raise_for_status()
    return r.json()


KEEP_FIELDS = ("answer", "recognized_text", "abstention_reason", "unverified_numbers", "answer_language",
               "language_retried", "is_sufficient_evidence", "latency_ms", "asr_warning")


def run_one(client: httpx.Client, target: Target, kind: str, item: tuple, repeat: int, clips: Path) -> dict:
    item_id, payload, expected = item
    record = {"target": target.name, "kind": kind, "item": item_id, "repeat": repeat, "expected": expected,
              "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    t0 = time.perf_counter()
    try:
        data = ask_text(client, payload) if kind == "text" else ask_voice(client, clips / item_id)
        record.update({k: data.get(k) for k in KEEP_FIELDS})
        record["sources"] = [[s.get("document_id"), s.get("page")] for s in data.get("sources", [])]
        record["error"] = None
    except (httpx.HTTPError, ValueError) as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"[:500]
    record["wall_sec"] = round(time.perf_counter() - t0, 3)
    return record


def run_target(target: Target, repeats: int, clips: Path, out: Path, lock: threading.Lock, seed: int) -> None:
    voice = [(clip, clip, gold) for clip, _, gold in VOICE_ITEMS]
    with httpx.Client(base_url=target.url, auth=target.auth, timeout=TIMEOUT_SEC) as client:
        t0 = time.perf_counter()
        try:
            ask_text(client, WARMUP_QUERY)
            print(f"[{target.name}] warm-up {time.perf_counter() - t0:.1f}s (discarded)", flush=True)
        except httpx.HTTPError as exc:
            print(f"[{target.name}] warm-up failed: {exc}", flush=True)
        for repeat in range(1, repeats + 1):
            rng = random.Random(seed * 1000 + repeat)
            work = [("text", it) for it in TEXT_ITEMS] + [("voice", it) for it in voice]
            rng.shuffle(work)
            for kind, item in work:
                record = run_one(client, target, kind, item, repeat, clips)
                with lock, open(out, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                status = record["error"] or f"{record['wall_sec']:.1f}s"
                print(f"[{target.name}] r{repeat} {kind:5} {record['item']:22} {status}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", action="append", type=parse_target, required=True)
    ap.add_argument("--repeats", type=int, default=10)
    ap.add_argument("--clips", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=20261114)
    args = ap.parse_args()
    if args.repeats < 1:
        ap.error("--repeats must be >= 1")
    missing = [c for c, _, _ in VOICE_ITEMS if not (args.clips / c).is_file()]
    if missing:
        ap.error(f"clips missing in {args.clips}: {missing}")
    args.out.parent.mkdir(parents=True, exist_ok=True)

    lock = threading.Lock()
    threads = [threading.Thread(target=run_target, args=(t, args.repeats, args.clips, args.out, lock, args.seed))
               for t in args.target]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    print(f"done -> {args.out}")


if __name__ == "__main__":
    main()
