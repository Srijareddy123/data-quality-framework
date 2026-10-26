"""Run a short sequence of loads through the checks and print what the audit log recorded.

python -m dqf.demo
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dqf.baseline import load_baseline
from dqf.loads import BATCH_ROWS, get_load, load_pool
from dqf.pipeline import run_validation
from dqf.store import AuditStore, make_engine

DATASET = "nyc_taxi_yellow"
SEQUENCE = [
    (0, None),
    (1, None),
    (2, None),
    (3, "nulls"),
    (4, None),
    (5, "schema_change"),
    (6, "value_drift"),
    (7, "row_loss"),
    (8, None),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="sqlite:///demo_audit.db", help="audit database URL")
    args = parser.parse_args()
    if args.db.startswith("sqlite:///"):
        Path(args.db.removeprefix("sqlite:///")).unlink(missing_ok=True)
    store = AuditStore(make_engine(args.db))
    baseline = load_baseline(expected_rows=BATCH_ROWS)
    pool = load_pool(baseline)

    print(f"{'run':>3}  {'batch':<22} {'rows':>4}  {'status':<8} findings")
    for index, defect in SEQUENCE:
        label = f"{index} " + (defect or "clean")
        df = get_load(pool, index, defect)
        run_id, status, found = run_validation(df, baseline, store, DATASET, label)
        checks = ", ".join(sorted({f.check + (f":{f.column}" if f.column else "") for f in found}))
        print(f"{run_id:>3}  {label:<22} {len(df):>4}  {status:<8} {checks or '-'}")
    counts = store.counts()
    print(f"\naudit log: {counts['runs']} runs, {counts['findings']} findings in {args.db}")
    print("Inspect it over HTTP with: make api   (then open /alerts and /health)")


if __name__ == "__main__":
    main()
