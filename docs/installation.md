# Installation

Tested on Windows 11 (office box, NVIDIA GPU) and Ubuntu 24.04 (AWS, CPU only). The original macOS scripts in `scripts/*.sh` are kept, but they assume Apple hardware and Homebrew and are no longer the reference setup.

## 1. Prerequisites

| Tool | Notes |
|---|---|
| Python 3.12 | Managed with [uv](https://docs.astral.sh/uv/) |
| Node 20+ and [pnpm](https://pnpm.io) | Frontend; use `pnpm`, not npm |
| ffmpeg | Audio decoding |
| Tesseract + Marathi data (`mar`) | Only for PDFs uploaded through the UI |
| Ollama | Only if `LLM_PROVIDER=ollama` |
| NVIDIA GPU + CUDA | Optional; needed for fast local speech-to-text |

Ubuntu: `sudo apt-get install ffmpeg tesseract-ocr tesseract-ocr-mar tesseract-ocr-eng build-essential`.
Windows: install ffmpeg and Tesseract and put them on `PATH`, or set `FFMPEG_PATH` / `TESSERACT_PATH` in `.env`.

## 2. Backend

```bash
uv venv --python 3.12 .venv

# CPU-only machines: install the small CPU build of torch first (avoids ~GBs of CUDA wheels)
uv pip install --python .venv/bin/python torch --index-url https://download.pytorch.org/whl/cpu

uv pip install --python .venv/bin/python -r requirements.txt
```

`IndicTransToolkit` in `requirements.txt` needs a C compiler. The backend does not import it, so on Windows without Visual C++ build tools you can install everything else and leave it out.

## 3. Data

`backend/data/` holds the corpus: `documents/` (GR PDFs, OCR results, `manifest.json`), `indexes/` (`faiss_index.bin`, `chunks_metadata.json`) and the SQLite database. A fresh clone needs either a copy of an existing `backend/data/` or a corpus build:

```bash
.venv/bin/python -m backend.app.services.rag.corpus.build --dry-run   # check first
.venv/bin/python -m backend.app.services.rag.corpus.build
```

The build uses OCR results that are already in `documents/ocr/`. Producing new OCR needs Surya on a GPU (`scripts/ocr_corpus.ps1`).

Models download on first use into the Hugging Face cache: `intfloat/multilingual-e5-small` (~0.5 GB) and any Whisper model selected. Converted Marathi Whisper models are expected under `models/ct2/<name>` (`ASR_CT2_DIR`).

## 4. Configuration (`.env`)

Copy `.env.example` to `.env`. Typical settings:

**Office / local GPU**
```ini
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen3.5:9b
OLLAMA_THINK=false
ASR_ACTIVE_MODEL=indicwhisper-medium-mr
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=int8_float16
EMBEDDING_DEVICE=cpu
```

**Cloud / CPU only (as on AWS)**
```ini
LLM_PROVIDER=bedrock
BEDROCK_REGION=ap-southeast-2
BEDROCK_MODEL_ID=qwen.qwen3-32b-v1:0
ASR_ACTIVE_MODEL=assemblyai        # needs ASSEMBLYAI_API_KEY; much weaker for Marathi than IndicWhisper
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
EMBEDDING_DEVICE=cpu
```

Bedrock credentials come from the standard AWS chain: an EC2 instance role in production, an AWS profile or environment variables elsewhere. Never put AWS keys in `.env`. The role or user needs `bedrock:InvokeModel` on the chosen model.

## 5. Run

```bash
# LLM (local option)
ollama pull qwen3.5:9b

# API
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

# Frontend dev server (proxies /api and /static to :8000)
cd frontend && pnpm install && pnpm dev     # http://localhost:5173
```

Production build of the frontend: `cd frontend && pnpm run build` (type-checks with `tsc -b`, output in `frontend/dist/`). Serve `dist/` from any static server that also proxies `/api` and `/static` to the backend.

Windows office box: `powershell -File scripts\start_services.ps1` starts Ollama, uvicorn and Vite detached.

Check it is up: `GET http://127.0.0.1:8000/api/health` shows the LLM provider and whether it is reachable, the ASR engines and the index size.

## 6. Tests

```bash
.venv/bin/python -m pytest backend/tests -q -p no:cacheprovider
```

The end-to-end tests (`test_api_e2e.py`) need the real index and a reachable LLM. On Windows, print Devanagari with `PYTHONUTF8=1`. When sending Marathi with `curl` from Git Bash, use `--data-binary @file.json` (UTF-8); inline `-d '…'` turns it into `???`.
