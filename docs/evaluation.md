# Evaluation

Every number here comes from a run that can be re-done, with the run file or script named. Sample sizes are stated; small samples are flagged as such. Earlier versions of this document listed ASR and RAG scores (e.g. "11.8% WER on standard Marathi", "Recall@3 0.942") and a "MacBook Air M2" hardware profile that do not trace to any recorded run. They have been removed.

---

## 1. Speech-to-text (ASR)

**Data.** RESPIN Marathi test split (2,170 utterances, 160 speakers, 4 dialect groups D1–D4) and FLEURS Marathi test split (1,015 utterances), frozen at fixed dataset revisions under `eval_data/`.
**Method.** `backend/app/evaluation/asr_bench/run.py bench`, the same normaliser for every engine, WER/CER via `jiwer`, 95% confidence intervals from a speaker-level paired bootstrap. Hardware: RTX 3060 Ti 8 GB, CUDA. RTF = decode time ÷ audio time.
**Runs.** `eval_data/runs/20261112-*/summary.json` on the office machine.

| Engine | RESPIN WER [95% CI] | RESPIN CER | FLEURS WER [95% CI] | FLEURS CER | RTF (RESPIN) |
|---|---|---|---|---|---|
| **indicwhisper-medium-mr** (AI4Bharat, CT2 int8_float16) | **26.9%** [25.1–28.7] | 6.1% | **22.8%** [21.7–23.9] | 8.3% | 0.117 |
| whisper-small-marathi (steja, CT2) | 57.7% [55.8–59.6] | 16.6% | 52.0% [50.6–53.2] | 17.9% | 0.059 |
| whisper large-v3-turbo | 81.6% [79.9–83.3] | 25.1% | 81.3% [80.1–82.6] | 25.3% | 0.053 |
| whisper medium | 90.6% [88.5–92.9] | 36.1% | 89.3% [87.6–91.3] | 37.6% | 0.247 |
| whisper small (original default) | 101.6% [100.2–103.0] | 39.0% | 106.3% [104.4–108.4] | 43.0% | 0.060 |

IndicWhisper by RESPIN dialect group: D1 38.1%, D2 26.5%, D3 14.1%. Dialect matters a lot. D1 is the hardest group.

**AssemblyAI** (cloud, Universal-2 for Marathi), side by side on a small sample (14 clips: 8 RESPIN + 6 FLEURS; `eval_data/runs/20261112-150510_assemblyai_vs_indicwhisper.json`): **86.5% WER** vs 26.9% for IndicWhisper on the same clips. It writes Marathi with Hindi forms (मिलते, है) and merges ण→न and ळ→ल. The sample is small but the gap is threefold on both datasets. The AWS deployment uses AssemblyAI only because it has no GPU.

### Read-aloud recordings (real speaker, live system)
Four clips (19–25 s each) read from the project's paragraph set and scored through the live `/api/speech/transcribe` (`scripts/score_readaloud.py`). Details: the vault note *readaloud_results_2026-11-12*.

- Long questions used to be cut off: Whisper's 30 s window holds only ~220 Devanagari characters. After splitting audio at pauses into ≤14 s pieces, pooled WER went from **23.5% → 10.6%**.
- End to end (`/api/chat/voice`): 3 of 4 answered correctly. One was wrongly refused by the evidence gate; that is fixed since.
- Four clips from one speaker is a smoke test, not a benchmark.

---

## 2. Retrieval

**Rate-table lookups.** 698 generated district × crop questions against the PMFBY 2025-26 rate tables, checking that a chunk containing the right row is retrieved:

| Retrieval | recall@1 | recall@4 |
|---|---|---|
| Semantic only, before the dedupe fix | 0.897 | 0.897 |
| Semantic only, after the dedupe fix | 0.897 | 0.961 |
| **Hybrid (semantic + district × crop table lookup)** | **0.971** | **1.000** |

The old dedupe compared only the first 100 characters, and every PMFBY chunk starts with the same long title, so each search collapsed to one result. Most remaining semantic misses were short district names (e.g. बीड) that e5 embeds poorly.

**Evidence gate.** On the three traps (Thane soybean, Mumbai rice, Ratnagiri soybean: district or crop not in the documents), the system refuses without calling the LLM. On real lookups (Ratnagiri rice, Nashik soybean, Gadchiroli cotton) it answers. Known gap: a scheme not in the corpus (e.g. solar pumps) is not caught by the gate, because it only knows districts and crops.

---

## 3. LLM answers

**Bake-off** (12 hand-read questions, office GPU, 2026-11-12):

| Model | s/answer | VRAM peak | Figures when evidence present | Traps refused (of 4) |
|---|---|---|---|---|
| qwen3.5:9b (chosen) | 8.1 | 7,927 MiB | correct | 2 |
| Aya Fire Q4 | 2.6 | 4,173 MiB | correct | 0 (invented figures) |
| Aya Fire Q8 | 3.2 | 5,531 MiB | correct | 0 |
| qwen3.5:4b | 5.6 | 5,430 MiB | mostly | invented a figure |

Automatic scores ranked the worse models higher twice, so every answer is read by a person.

**Bedrock Qwen3-32B** (AWS deployment): not yet run through the bake-off. One live check (the Namo Shetkari question) retrieved 4/4 pages of the correct GR and answered in Marathi in 4.6 s on the server. It stated the instalments correctly and said "insufficient evidence" for eligibility, which the top-4 excerpts did not contain.

**Numeric guard.** Numbers in an answer that do not appear in the evidence or the question get a warning. Known false positives: derived totals (₹6,000 = 3 × ₹2,000), Marathi number words and some unit conversions. A v2 is planned.

---

## 4. Resources and latency

| Setup | Measured |
|---|---|
| Office: qwen3.5:9b + IndicWhisper loaded | VRAM peak 7,867–7,931 of 8,192 MiB; backend RSS ~2.1 GB |
| AWS: typed question, Bedrock Qwen3-32B | 4.6 s server-side; 5.8 s round trip from India |
| AWS: first request after install | +19 s once, to download `multilingual-e5-small` |

---

## 5. Automated tests

`pytest backend/tests`: 357 passed on the AWS server and 357 on the office PC on 2026-11-14 (real index; the end-to-end scenarios ran against live Bedrock on AWS and Ollama on office). The tests cover chunking, OCR corrections, table grids, retrieval dedupe, table lookup, the evidence gate, the numeric guard, answer language, dialect normalisation, ASR registry and long-audio splitting, the Bedrock client (with faked AWS), the public corpus-source list, the benchmark scorer and the API scenarios.

---

## 6. Deployment comparison: office (local) vs AWS, 2026-11-14

Each item was sent end to end through `/api/chat` and `/api/chat/voice` on both deployments, 10 times, from one client on the office network: 320 requests and 0 errors. The two deployments run the same code and index; only `.env` differs. Office uses Ollama `qwen3.5:9b` and IndicWhisper on an RTX 3060 Ti. AWS uses Bedrock Qwen3-32B and AssemblyAI on a 2-vCPU EC2 instance in Sydney.

Items:
- the 12 graded questions from §3: 8 with figures checked against the GR tables, and 4 that must be refused;
- the 4 read-aloud clips from §1, with every figure the question asks for required.

Each repeat used a seeded shuffled order, the same on both deployments. The scoring rules were fixed before the full run (`scripts/bench_score.py`, tested in `backend/tests/test_bench_score.py`). Raw data: `eval_data/runs/20261114_deploy_bench.jsonl`.

| | Office | AWS |
|---|---|---|
| Typed correct | 120/120 = 100% (95% CI 96.9–100) | 87/120 = 72.5% (63.9–79.7) |
| … answerable with the right figure | 80/80 | 47/80 |
| … traps refused | 40/40 | 40/40 |
| Voice correct | 40/40 = 100% (91.2–100) | 0/40 = 0% (0–8.8) |
| Speech-to-text WER, 4 clips × 10 | 10.6% | 62.8% |
| Answerable questions wrongly refused | 0/120 | 12/120 |
| Invented figures, hand-checked | 1/160 | 0/160 |
| Median / p90 time, typed | 8.79 / 8.99 s | 5.21 / 5.55 s |
| Median / p90 time, voice | 11.77 / 12.39 s | 12.54 / 14.18 s |

Paired by item and repeat:
- **Typed:** office alone was correct in 33 pairs and AWS alone in 0 (exact McNemar p ≈ 2e-10).
- **Voice:** 40 against 0 (p ≈ 2e-12).
- **Latency:** AWS was 3.6 s faster per typed question (bootstrap 95% CI 3.5–4.7 s) and 0.8 s slower per voice question.

Where AWS failed:
- **Typed questions.** It answered 3 table lookups in all 10 repeats without the figure: Gadchiroli and Nashik cotton sum insured, and the Nashik soybean premium. It retrieved the same pages as office.
- **Voice questions.** AssemblyAI's transcripts never let an answer reach the asked figure.

Office's one real error was a voice answer that treated "2 acres" as 2 ha and wrote ₹1,18,000 instead of about ₹47,800; the numeric guard flagged it. The guard raised 24 other flags across both deployments, and all of them were false alarms:
- figures the GR writes in words ("५० हजार");
- the Namo total (3 × ₹2,000);
- dates and page numbers.

So the flag rate is not an error rate; numeric guard v2 is meant to remove these.

Limits: 12 questions and 4 clips from one speaker. The 10 repeats show consistency on these items, not accuracy on questions in general.
