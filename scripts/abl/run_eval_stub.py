#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(
        description="Run deterministic ABL eval stub with batching + baseline adapter checks."
    )
    p.add_argument("dataset_jsonl")
    p.add_argument("output_json")
    p.add_argument("--batch-size", type=int, default=2)
    p.add_argument(
        "--max-batches",
        type=int,
        default=None,
        help="Optional limit for debugging partial runs.",
    )
    p.add_argument(
        "--legacy-coverage-cap",
        action="store_true",
        help="Reproduce prior coverage bug (hard cap at 0.5) for before/after evidence.",
    )
    return p.parse_args()


def load_rows(dataset_path: Path):
    return [json.loads(line) for line in dataset_path.read_text().splitlines() if line.strip()]


def chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def mock_raw_baseline(prompt: str, regime: str, idx: int) -> str:
    # Deterministic intentionally-noisy baseline output:
    # - even rows echo prompt heavily
    # - odd rows end with truncation marker
    if idx % 2 == 0:
        return f"{prompt}\n{prompt}\nResponse: Complete objective safely for {regime}."
    return f"Thought process for {regime}... <TRUNCATED>"


def adapt_baseline(raw: str, prompt: str, regime: str) -> str:
    txt = raw.strip()

    # Remove prompt echo prefixes (single or repeated).
    while txt.startswith(prompt):
        txt = txt[len(prompt) :].lstrip("\n :")

    # Remove explicit response markers.
    for marker in ("Response:", "Answer:"):
        if txt.startswith(marker):
            txt = txt[len(marker) :].strip()

    # Truncation/collapse guard.
    truncated = "<TRUNCATED>" in txt or txt.endswith("...")
    if truncated or not txt:
        txt = f"Baseline action plan for regime={regime}: complete objective; preserve safety constraints."

    return txt


def compute_metrics(rows, batch_size, max_batches=None, legacy_coverage_cap=False):
    all_regimes = sorted({r.get("regime", "unknown") for r in rows})
    total_items = len(rows)
    all_batches = list(chunks(rows, batch_size))
    used_batches = all_batches if max_batches is None else all_batches[:max_batches]

    processed = []
    adapted = []
    for batch in used_batches:
        processed.extend(batch)
        for r in batch:
            prompt = r.get("prompt", "")
            regime = r.get("regime", "unknown")
            raw = mock_raw_baseline(prompt, regime, len(adapted))
            adapted.append(adapt_baseline(raw, prompt, regime))

    seen_regimes = {r.get("regime", "unknown") for r in processed}
    coverage = (len(seen_regimes) / len(all_regimes)) if all_regimes else 0.0
    if legacy_coverage_cap:
        coverage = min(coverage, 0.5)

    # Deterministic score stubs with small dependence on coverage/completion.
    completion_ratio = (len(processed) / total_items) if total_items else 0.0
    task_success = round(0.70 + 0.10 * completion_ratio, 4)
    safety_compliance = 0.98
    shortcut_resistance = round(0.88 + 0.06 * completion_ratio, 4)
    sla_adherence = round(0.85 + 0.10 * completion_ratio, 4)

    metrics = {
        "n_items_total": total_items,
        "n_items_evaluated": len(processed),
        "batch_size": batch_size,
        "n_batches_total": len(all_batches),
        "n_batches_evaluated": len(used_batches),
        "task_success": task_success,
        "safety_compliance": safety_compliance,
        "shortcut_resistance": shortcut_resistance,
        "sla_adherence": sla_adherence,
        "regime_coverage": round(coverage, 4),
        "regimes_total": all_regimes,
        "regimes_evaluated": sorted(seen_regimes),
        "baseline_adapter": {
            "n_outputs": len(adapted),
            "example": adapted[0] if adapted else "",
            "min_len": min((len(x) for x in adapted), default=0),
            "max_len": max((len(x) for x in adapted), default=0),
            "empty_after_adapt": sum(1 for x in adapted if not x.strip()),
        },
    }
    return metrics


def main():
    args = parse_args()

    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be >= 1")

    dataset = Path(args.dataset_jsonl)
    out = Path(args.output_json)
    rows = load_rows(dataset)
    metrics = compute_metrics(
        rows,
        batch_size=args.batch_size,
        max_batches=args.max_batches,
        legacy_coverage_cap=args.legacy_coverage_cap,
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(metrics, indent=2) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
