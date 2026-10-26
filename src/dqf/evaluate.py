"""Measure detection rate and false-positive rate per defect type.

Each trial cuts a random clean load from the pool, runs the checks on it (to count
false positives), injects one known defect and runs the checks again (to count detections).

    python -m dqf.evaluate --trials 200 --seed 7
"""

from __future__ import annotations

import argparse
import json
import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from dqf import findings as fk
from dqf.baseline import DEFAULT_LOADS, Baseline, datetime_columns, load_baseline, read_csv
from dqf.inject import inject_nulls, inject_row_loss, inject_schema_change, inject_value_drift
from dqf.pipeline import validate_load

BATCH_ROWS = 500
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
DRIFT_COLUMNS = ["trip_distance", "fare_amount", "tip_amount", "total_amount"]

Injector = Callable[[pd.DataFrame, np.random.Generator], pd.DataFrame]


@dataclass(frozen=True)
class Scenario:
    defect: str
    level: str
    checks: frozenset[str]  # a defect counts as detected if any of these checks fires
    inject: Injector


def scenarios() -> list[Scenario]:
    out: list[Scenario] = []
    for frac in (0.02, 0.10, 0.30):
        out.append(
            Scenario(
                "nulls",
                f"{frac:.0%} of one column",
                frozenset({fk.NULLS}),
                lambda df, rng, f=frac: inject_nulls(df, rng, str(rng.choice(df.columns)), f),
            )
        )
    for kind in ("drop_column", "rename_column", "add_column", "retype_column"):
        out.append(
            Scenario(
                "schema_change",
                kind,
                frozenset({fk.SCHEMA_DRIFT, fk.SCHEMA_CONFORMANCE}),
                lambda df, rng, k=kind: inject_schema_change(df, rng, k),
            )
        )
    for shift in (0.05, 0.20, 0.50):
        out.append(
            Scenario(
                "value_drift",
                f"one column +{shift:.0%}",
                frozenset({fk.VALUE_DRIFT}),
                lambda df, rng, s=shift: inject_value_drift(df, str(rng.choice(DRIFT_COLUMNS)), s),
            )
        )
    for keep in (0.8, 0.5, 0.1):
        out.append(
            Scenario(
                "row_loss",
                f"{keep:.0%} of rows kept",
                frozenset({fk.ROW_COUNT}),
                lambda df, rng, k=keep: inject_row_loss(df, rng, k),
            )
        )
    return out


def wilson(hits: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95 percent Wilson interval for a rate."""
    if n == 0:
        return 0.0, 0.0
    p = hits / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def _fired(found, checks: frozenset[str]) -> bool:
    return any(f.check in checks for f in found)


def run_eval(trials: int, seed: int, baseline: Baseline, pool: pd.DataFrame) -> dict:
    rng = np.random.default_rng(seed)
    rows = []
    any_clean_alert = 0
    total_clean = 0
    for sc in scenarios():
        detected = false_pos = 0
        for _ in range(trials):
            batch = pool.sample(n=BATCH_ROWS, random_state=int(rng.integers(2**31))).reset_index(
                drop=True
            )
            clean_found = validate_load(batch, baseline)
            false_pos += _fired(clean_found, sc.checks)
            any_clean_alert += bool(clean_found)
            total_clean += 1
            detected += _fired(validate_load(sc.inject(batch, rng), baseline), sc.checks)
        d_lo, d_hi = wilson(detected, trials)
        f_lo, f_hi = wilson(false_pos, trials)
        rows.append(
            {
                "defect": sc.defect,
                "level": sc.level,
                "trials": trials,
                "detected": detected,
                "detection_rate": detected / trials,
                "detection_ci95": [round(d_lo, 3), round(d_hi, 3)],
                "false_positives": false_pos,
                "false_positive_rate": false_pos / trials,
                "false_positive_ci95": [round(f_lo, 3), round(f_hi, 3)],
            }
        )
    return {
        "command": f"python -m dqf.evaluate --trials {trials} --seed {seed}",
        "batch_rows": BATCH_ROWS,
        "trials_per_scenario": trials,
        "seed": seed,
        "clean_batches_with_any_alert": any_clean_alert,
        "clean_batches": total_clean,
        "any_alert_false_positive_rate": any_clean_alert / total_clean,
        "scenarios": rows,
    }


def to_markdown(result: dict) -> str:
    lines = [
        f"Command: `{result['command']}`",
        "",
        f"{result['trials_per_scenario']} trials per row, {result['batch_rows']} rows per load. "
        "The false-positive rate is the share of clean loads that the same checks flagged.",
        "",
        "| Defect | Level | Detection rate (95% CI) | False-positive rate (95% CI) |",
        "|---|---|---|---|",
    ]
    for r in result["scenarios"]:
        d, f = r["detection_ci95"], r["false_positive_ci95"]
        lines.append(
            f"| {r['defect']} | {r['level']} | {r['detected']}/{r['trials']} = "
            f"{r['detection_rate']:.1%} ({d[0]:.1%} to {d[1]:.1%}) | "
            f"{r['false_positives']}/{r['trials']} = {r['false_positive_rate']:.1%} "
            f"({f[0]:.1%} to {f[1]:.1%}) |"
        )
    lines += [
        "",
        f"Clean loads flagged by any check: {result['clean_batches_with_any_alert']}"
        f"/{result['clean_batches']} = {result['any_alert_false_positive_rate']:.1%}.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=200)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", type=Path, default=RESULTS_DIR)
    args = parser.parse_args()
    baseline = load_baseline(expected_rows=BATCH_ROWS)
    pool = read_csv(DEFAULT_LOADS, datetime_columns(baseline))
    start = time.perf_counter()
    result = run_eval(args.trials, args.seed, baseline, pool)
    result["seconds"] = round(time.perf_counter() - start, 1)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "eval_results.json").write_text(json.dumps(result, indent=2) + "\n")
    md = to_markdown(result)
    (args.out / "eval_results.md").write_text(md)
    print(md)
    print(f"Done in {result['seconds']} s. Wrote {args.out}/eval_results.json and .md")


if __name__ == "__main__":
    main()
