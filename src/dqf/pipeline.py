"""Run every check on one load and write the result to the audit log."""

from __future__ import annotations

import pandas as pd

from dqf.baseline import Baseline, schema_of
from dqf.drift import schema_drift, value_drift
from dqf.findings import ERROR, WARNING, Finding
from dqf.ge_checks import run_ge_checks
from dqf.store import AuditStore

PASSED, WARNED, FAILED = "passed", "warning", "failed"


def validate_load(
    df: pd.DataFrame, baseline: Baseline, previous_schema: dict[str, str] | None = None
) -> list[Finding]:
    """Pure function: all findings for one load. previous_schema defaults to the baseline."""
    previous = previous_schema if previous_schema is not None else baseline.schema
    return [
        *run_ge_checks(df, baseline),
        *schema_drift(df, previous),
        *value_drift(df, baseline),
    ]


def status_of(found: list[Finding]) -> str:
    if any(f.severity == ERROR for f in found):
        return FAILED
    return WARNED if any(f.severity == WARNING for f in found) else PASSED


def run_validation(
    df: pd.DataFrame,
    baseline: Baseline,
    store: AuditStore,
    dataset: str,
    batch_id: str,
) -> tuple[int, str, list[Finding]]:
    """Validate a load and record it. Returns (run id, status, findings)."""
    found = validate_load(df, baseline, store.latest_schema(dataset))
    status = status_of(found)
    run_id = store.record_run(dataset, batch_id, len(df), status, found, schema_of(df))
    return run_id, status, found
