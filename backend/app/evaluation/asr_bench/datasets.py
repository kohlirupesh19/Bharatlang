"""Loaders for the frozen ASR test sets downloaded by scripts/fetch_eval.py."""
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional

import numpy as np
import pyarrow.parquet as pq
import soundfile as sf
from scipy.signal import resample_poly

TARGET_SR = 16000
EVAL_ROOT = Path(__file__).resolve().parents[4] / "eval_data"


@dataclass(frozen=True)
class Sample:
    utt_id: str
    speaker: str
    reference: str
    dialect: str
    duration: float
    audio: np.ndarray  # mono float32 at 16 kHz


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    files_glob: str
    ref_column: str
    bootstrap_unit: str  # "speaker" or "utterance"


DATASETS: Dict[str, DatasetSpec] = {
    "fleurs": DatasetSpec("fleurs", "fleurs/mr_in/test/*.parquet", "raw_transcription", "utterance"),
    "respin": DatasetSpec("respin", "respin/data/mr/*.parquet", "transcription", "speaker"),
}


def _decode(audio_cell: dict) -> np.ndarray:
    data, sr = sf.read(io.BytesIO(audio_cell["bytes"]), dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    if sr != TARGET_SR:
        gcd = np.gcd(sr, TARGET_SR)
        mono = resample_poly(mono, TARGET_SR // gcd, sr // gcd).astype(np.float32)
    return mono


def _row_to_sample(spec: DatasetSpec, row: dict, audio: np.ndarray) -> Sample:
    if spec.name == "respin":
        return Sample(row["id"], str(row["speaker_id"]), row[spec.ref_column], row["dialect"],
                      float(row["duration"]), audio)
    # FLEURS has no speaker IDs; each recording path is its own bootstrap unit.
    return Sample(f"{row['id']}:{row['path']}", row["path"], row[spec.ref_column], "standard",
                  len(audio) / TARGET_SR, audio)


def dataset_revision(name: str) -> Optional[str]:
    manifest = EVAL_ROOT / "manifest.json"
    if not manifest.exists():
        return None
    key = {"fleurs": "fleurs_mr_in_test", "respin": "respin_mr_test"}[name]
    return json.loads(manifest.read_text(encoding="utf-8")).get(key, {}).get("revision")


def iter_samples(name: str, dialects: Optional[List[str]] = None, limit: Optional[int] = None) -> Iterator[Sample]:
    """Yield samples in a fixed, file-sorted order so runs are directly comparable."""
    if name not in DATASETS:
        raise ValueError(f"Unknown dataset {name!r}; choose from {sorted(DATASETS)}")
    spec = DATASETS[name]
    files = sorted(EVAL_ROOT.glob(spec.files_glob))
    if not files:
        raise FileNotFoundError(f"No files for {name} under {EVAL_ROOT}; run scripts/fetch_eval.py")
    emitted = 0
    for path in files:
        for batch in pq.ParquetFile(path).iter_batches(batch_size=64):
            for row in batch.to_pylist():
                if dialects and row.get("dialect") not in dialects:
                    continue
                yield _row_to_sample(spec, row, _decode(row["audio"]))
                emitted += 1
                if limit is not None and emitted >= limit:
                    return
