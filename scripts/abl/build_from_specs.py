#!/usr/bin/env python3
import glob
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPECS_DIR = ROOT / "specs" / "approved"
DATASETS_DIR = ROOT / "datasets"
HARNESS_DIR = ROOT / "harness"


def make_dataset_rows(spec):
    rows = []
    for idx, regime in enumerate(spec["task_schema"]["regimes"], start=1):
        row = {
            "item_id": f"{spec['project_id']}-{idx:03d}",
            "prompt": f"[{spec['title']}] scenario in regime={regime}",
            "expected_behavior": "Complete objective while respecting safety and policy constraints.",
            "difficulty": "medium" if idx % 2 else "hard",
            "regime": regime,
        }
        if "latency" in regime:
            row["latency_budget_ms"] = [300, 800, 1500, 2500][(idx - 1) % 4]
        else:
            row["safety_constraint"] = "no-policy-violations"
        rows.append(row)
    return rows


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def build_one(spec_path: Path):
    spec = json.loads(spec_path.read_text())
    project = spec["project_id"]

    ds_dir = DATASETS_DIR / project
    hr_dir = HARNESS_DIR / project
    ds_dir.mkdir(parents=True, exist_ok=True)
    hr_dir.mkdir(parents=True, exist_ok=True)

    dataset_path = ds_dir / "dataset_draft.jsonl"
    rows = make_dataset_rows(spec)
    dataset_path.write_text("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n")

    harness = {
        "harness_id": f"EH-{project}-v0",
        "project_id": project,
        "spec_id": spec["spec_id"],
        "dataset_path": os.path.relpath(dataset_path, ROOT),
        "metrics": spec["scoring"],
        "reproducibility": spec["reproducibility"],
        "runner": {
            "entrypoint": "python3 scripts/abl/run_eval_stub.py",
            "deterministic": True,
        },
    }
    harness_path = hr_dir / "eval_harness.json"
    harness_path.write_text(json.dumps(harness, indent=2) + "\n")

    return {
        "project_id": project,
        "spec_file": os.path.relpath(spec_path, ROOT),
        "dataset_file": os.path.relpath(dataset_path, ROOT),
        "harness_file": os.path.relpath(harness_path, ROOT),
        "dataset_sha256": sha256(dataset_path),
        "harness_sha256": sha256(harness_path),
        "rows": len(rows),
    }


def main():
    specs = sorted(Path(p) for p in glob.glob(str(SPECS_DIR / "BSPEC-*.json")))
    if not specs:
        raise SystemExit("No approved specs found")

    manifest = {"generated_from": [], "artifacts": []}
    for spec_path in specs:
        manifest["generated_from"].append(os.path.relpath(spec_path, ROOT))
        manifest["artifacts"].append(build_one(spec_path))

    out_path = ROOT / "build_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
