"""Known defects, injected into a clean load so detection can be measured.

Every function returns a new frame and leaves its input untouched.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from dqf.baseline import NUMBER, schema_of


def inject_nulls(df: pd.DataFrame, rng: np.random.Generator, column: str, fraction: float):
    out = df.copy()
    rows = rng.choice(len(out), size=int(round(fraction * len(out))), replace=False)
    out.iloc[rows, out.columns.get_loc(column)] = np.nan
    return out


def inject_row_loss(df: pd.DataFrame, rng: np.random.Generator, keep: float):
    keep_n = int(round(keep * len(df)))
    return df.iloc[np.sort(rng.choice(len(df), size=keep_n, replace=False))].reset_index(drop=True)


def inject_schema_change(df: pd.DataFrame, rng: np.random.Generator, kind: str):
    out = df.copy()
    if kind == "drop_column":
        return out.drop(columns=[str(rng.choice(out.columns))])
    if kind == "rename_column":
        old = str(rng.choice(out.columns))
        return out.rename(columns={old: old + "_v2"})
    if kind == "add_column":
        out["surge_flag"] = 0
        return out
    if kind == "retype_column":
        numeric = [c for c, t in schema_of(out).items() if t == NUMBER]
        col = str(rng.choice(numeric))
        out[col] = out[col].astype(str)
        return out
    raise ValueError(f"unknown schema change: {kind}")


def inject_value_drift(df: pd.DataFrame, column: str, shift: float):
    """Scale a numeric column, for example shift=0.2 makes every value 20 percent larger."""
    out = df.copy()
    out[column] = out[column] * (1 + shift)
    return out
