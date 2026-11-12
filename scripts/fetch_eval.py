"""Download frozen ASR test sets and record exact revisions."""
import json
import sys
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download, snapshot_download

ROOT = Path(r"C:\dev\Bharatlang\eval_data")
api = HfApi()
manifest = {}

# FLEURS Marathi test: HF's auto-converted parquet (the repo itself uses a loading script)
fleurs_rev = api.dataset_info("google/fleurs", revision="refs/convert/parquet").sha
p = hf_hub_download("google/fleurs", "mr_in/test/0000.parquet", repo_type="dataset",
                    revision="refs/convert/parquet", local_dir=ROOT / "fleurs")
manifest["fleurs_mr_in_test"] = {"repo": "google/fleurs", "revision": fleurs_rev, "file": str(p)}
print("fleurs ok", p)

# RESPIN Marathi test (evaluation only; never train on this mirror)
respin_rev = api.dataset_info("rimrafadii/respin-iisc").sha
d = snapshot_download("rimrafadii/respin-iisc", repo_type="dataset", revision=respin_rev,
                      allow_patterns=["data/mr/*", "IISc_RESPIN_test_mr/meta_test_mr.json",
                                      "IISc_RESPIN_test_mr/README.md", "README.md"],
                      local_dir=ROOT / "respin")
manifest["respin_mr_test"] = {"repo": "rimrafadii/respin-iisc", "revision": respin_rev, "dir": str(d),
                              "note": "evaluation only"}
print("respin ok", d)

(ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps(manifest, indent=2))
