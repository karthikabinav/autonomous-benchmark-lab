#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
manifest = json.loads((ROOT / "build_manifest.json").read_text())
assert len(manifest["artifacts"]) >= 2

for a in manifest["artifacts"]:
    ds = ROOT / a["dataset_file"]
    hr = ROOT / a["harness_file"]
    assert ds.exists(), ds
    assert hr.exists(), hr

    rows = [json.loads(line) for line in ds.read_text().splitlines() if line.strip()]
    assert len(rows) == a["rows"]
    harness = json.loads(hr.read_text())
    assert harness["dataset_path"] == a["dataset_file"]
    assert harness["project_id"] == a["project_id"]

print("ABL build output tests passed")
