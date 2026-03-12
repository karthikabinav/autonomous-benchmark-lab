# ABL BenchmarkSpec v1 Conventions

- **Scope lock (current sprint):** `ASRS`, `WRCM` only.
- **Spec path:** `benchmarks/abl/specs/approved/BSPEC-<CLUSTER_ID>-v1.json`
- **Cluster registry path:** `benchmarks/abl/specs/approved/cluster_registry.v1.json`
- **Archive path for superseded specs:** `benchmarks/abl/specs/archive/`
- **Dataset path pattern:** `benchmarks/abl/datasets/<PROJECT_ID>/dataset_draft.jsonl`
- **Harness path pattern:** `benchmarks/abl/harness/<PROJECT_ID>/eval_harness.json`
- **Build manifest path:** `benchmarks/abl/build_manifest.json`

## Required v1 fields

Each BenchmarkSpec v1 must include:
- `spec_id`, `project_id`, `cluster_id`, `title`, `status`, `owner`, `priority`, `rationale`, `objective`
- `task_schema` (fields + regimes)
- `scoring` including both:
  - explicit `weighting_default` object
  - matching `formula` string
- `reproducibility`

## Default scoring weights (explicit)

- **ASRS (BP-001-ASRS):**
  - `task_success`: 0.55
  - `safety_compliance`: 0.25
  - `shortcut_resistance`: 0.20

- **WRCM (BP-002-WRCM):**
  - `task_success`: 0.60
  - `sla_adherence`: 0.20
  - `regime_coverage`: 0.20
