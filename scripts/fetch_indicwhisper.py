"""Download and safely extract IndicWhisper Marathi into its own directory."""
import sys
import urllib.request
import zipfile
from pathlib import Path

URL = "https://indicwhisper.objectstore.e2enetworks.net/marathi_models.zip"
dest = Path(r"C:\dev\Bharatlang\models\downloads\indicwhisper_mr")
dest.mkdir(parents=True, exist_ok=True)
archive = dest / "marathi_models.zip"
if not archive.exists():
    urllib.request.urlretrieve(URL, archive)
print("archive bytes", archive.stat().st_size)
with zipfile.ZipFile(archive) as zf:
    root = (dest / "extracted").resolve()
    for member in zf.infolist():
        target = (root / member.filename).resolve()
        if not str(target).startswith(str(root)):
            sys.exit(f"unsafe path in archive: {member.filename}")
    zf.extractall(root)
    names = zf.namelist()
print(len(names), "entries; sample:", names[:15])
