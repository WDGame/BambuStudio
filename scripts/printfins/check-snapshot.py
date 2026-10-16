"""Verify the pinned original snapshot, optionally against an upstream source folder."""
import hashlib
import json
import pathlib
import sys

snapshot = pathlib.Path(__file__).resolve().parents[2] / "resources/printfins/vendor"
manifest = json.loads((snapshot / "ORIGIN.json").read_text(encoding="utf-8"))
roots = [snapshot] + ([pathlib.Path(sys.argv[1])] if len(sys.argv) > 1 else [])
actual_files = {p.relative_to(snapshot).as_posix() for p in snapshot.rglob("*") if p.is_file()}
if actual_files != set(manifest["files"]) | {"ORIGIN.json"}:
    raise SystemExit("Snapshot contains missing or unexpected files")
for root in roots:
    for name, expected in manifest["files"].items():
        data = (root / name).read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise SystemExit(f"Snapshot mismatch: {root / name}")
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if blob != manifest["git_blobs"][name]:
            raise SystemExit(f"Upstream Git blob mismatch: {root / name}")
    print(f"PASS: {len(manifest['files'])} original files match SHA-256 and Git blobs in {root}")
