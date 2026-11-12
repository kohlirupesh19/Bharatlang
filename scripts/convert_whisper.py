"""Convert a HF Whisper checkpoint to CTranslate2, materialising tokenizer.json if the repo lacks it.

usage: convert_whisper.py <hf_repo_id | local_dir> <output_dir> [quantization]
"""
import sys
import tempfile
from pathlib import Path

from ctranslate2.converters import TransformersConverter
from huggingface_hub import snapshot_download
from transformers import WhisperFeatureExtractor, WhisperForConditionalGeneration, WhisperTokenizerFast

repo, out_dir = sys.argv[1], Path(sys.argv[2])
quant = sys.argv[3] if len(sys.argv) > 3 else "float16"
if out_dir.exists():
    sys.exit(f"{out_dir} already exists; refusing to overwrite")

src = Path(repo) if Path(repo).is_dir() else Path(snapshot_download(repo))  # local dir or HF repo id
with tempfile.TemporaryDirectory() as tmp:
    staged = Path(tmp) / "model"
    WhisperForConditionalGeneration.from_pretrained(src).save_pretrained(staged)
    # Saved separately: in transformers 5 the combined processor no longer writes these two files.
    WhisperTokenizerFast.from_pretrained(src).save_pretrained(staged)      # tokenizer.json
    WhisperFeatureExtractor.from_pretrained(src).save_pretrained(staged)   # preprocessor_config.json
    missing = [f for f in ("tokenizer.json", "preprocessor_config.json") if not (staged / f).exists()]
    if missing:
        sys.exit(f"staging incomplete, missing {missing}")
    TransformersConverter(str(staged), copy_files=["tokenizer.json", "preprocessor_config.json"]).convert(
        str(out_dir), quantization=quant)
print("converted", repo, "->", out_dir, "revision path", src)
