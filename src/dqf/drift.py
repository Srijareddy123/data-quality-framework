"""Drift checks: upstream schema changes and shifts in numeric distributions."""

from __future__ import annotations

import pandas as pd
from scipy.stats import ks_2samp

from dqf.baseline import NUMBER, Baseline, schema_of
from dqf.findings import ERROR, SCHEMA_DRIFT, VALUE_DRIFT, WARNING, Finding

KS_ALPHA = 0.001
MIN_ROWS_FOR_KS = 30


def diff_schema(previous: dict[str, str], current: dict[str, str]) -> list[str]:
    changes = [f"column removed: {c}" for c in sorted(set(previous) - set(current))]
    changes += [f"column added: {c}" for c in sorted(set(current) - set(previous))]
    for col in sorted(set(previous) & set(current)):
        if previous[col] != current[col]:
            changes.append(f"type changed: {col} {previous[col]} to {current[col]}")
    return changes


def schema_drift(df: pd.DataFrame, previous: dict[str, str]) -> list[Finding]:
    """Compare this load's schema with the schema of the previous load."""
    changes = diff_schema(previous, schema_of(df))
    return [Finding(SCHEMA_DRIFT, ERROR, "; ".join(changes))] if changes else []


def value_drift(df: pd.DataFrame, baseline: Baseline) -> list[Finding]:
    """Two-sample KS test of each numeric column against the reference file."""
    if len(df) < MIN_ROWS_FOR_KS:
        return []
    findings = []
    for col in baseline.numeric_columns:
        if col not in df.columns or schema_of(df[[col]])[col] != NUMBER:
            continue
        new, ref = df[col].dropna(), baseline.reference[col].dropna()
        if len(new) < MIN_ROWS_FOR_KS:
            continue
        result = ks_2samp(new, ref)
        if result.pvalue < KS_ALPHA:
            msg = f"KS statistic {result.statistic:.3f}, p-value {result.pvalue:.2g}"
            findings.append(Finding(VALUE_DRIFT, WARNING, msg, col))
    return findings
