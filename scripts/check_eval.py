import collections, glob, json, sys
import pyarrow.parquet as pq
sys.stdout.reconfigure(encoding="utf-8")
R = r"C:\dev\Bharatlang\eval_data"
f = pq.read_table(glob.glob(R + r"\fleurs\mr_in\test\*.parquet")[0])
print("FLEURS rows", f.num_rows, "cols", f.column_names)
print("  sample:", f.column("transcription")[0].as_py()[:120])
files = sorted(glob.glob(R + r"\respin\data\mr\*.parquet"))
t = pq.read_table(files[0])
print("RESPIN files", len(files), "cols", t.column_names)
rows = sum(pq.ParquetFile(x).metadata.num_rows for x in files)
print("RESPIN rows", rows)
cols = [c for c in t.column_names if c not in ("audio",)]
meta = collections.Counter()
spk = collections.defaultdict(set)
for x in files:
    tb = pq.read_table(x, columns=cols)
    for r in tb.to_pylist():
        meta[r.get("dialect")] += 1
        spk[r.get("dialect")].add(r.get("speaker_id"))
print("RESPIN by dialect:", dict(meta), "speakers:", {k: len(v) for k, v in spk.items()})
print("  sample row:", {k: v for k, v in tb.to_pylist()[0].items()})
