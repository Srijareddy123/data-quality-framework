"""Cut demo loads out of the sample pool, optionally with a known defect."""

from __future__ import annotations

import numpy as np
import pandas as pd

from dqf.baseline import DEFAULT_LOADS, Baseline, datetime_columns, read_csv
from dqf.inject import inject_nulls, inject_row_loss, inject_schema_change, inject_value_drift

BATCH_ROWS = 500
DEFECTS = ("nulls", "schema_change", "value_drift", "row_loss")


def load_pool(baseline: Baseline) -> pd.DataFrame:
    return read_csv(DEFAULT_LOADS, datetime_columns(baseline))


def n_batches(pool: pd.DataFrame) -> int:
    return len(pool) // BATCH_ROWS


def get_load(
    pool: pd.DataFrame, batch_index: int, defect: str | None = None, seed: int = 0
) -> pd.DataFrame:
    """Batch number batch_index (wraps around), with one defect injected if asked."""
    start = (batch_index % n_batches(pool)) * BATCH_ROWS
    batch = pool.iloc[start : start + BATCH_ROWS].reset_index(drop=True)
    rng = np.random.default_rng(seed + batch_index)
    if defect is None:
        return batch
    if defect == "nulls":
        return inject_nulls(batch, rng, "fare_amount", 0.15)
    if defect == "schema_change":
        return inject_schema_change(batch, rng, "retype_column")
    if defect == "value_drift":
        return inject_value_drift(batch, "trip_distance", 0.30)
    if defect == "row_loss":
        return inject_row_loss(batch, rng, 0.2)
    raise ValueError(f"unknown defect {defect!r}, choose from {DEFECTS}")
