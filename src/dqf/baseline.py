"""The contract a load is checked against, built from a known-good reference file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

NUMBER, STRING, DATETIME, BOOLEAN = "number", "string", "datetime", "boolean"

DEFAULT_REFERENCE = Path(__file__).resolve().parents[2] / "data" / "sample" / "reference.csv"
DEFAULT_LOADS = DEFAULT_REFERENCE.with_name("loads.csv")


def logical_type(series: pd.Series) -> str:
    """Collapse pandas dtypes into four logical types so int and float count as one."""
    if pd.api.types.is_bool_dtype(series):
        return BOOLEAN
    if pd.api.types.is_numeric_dtype(series):
        return NUMBER
    if pd.api.types.is_datetime64_any_dtype(series):
        return DATETIME
    return STRING


def schema_of(df: pd.DataFrame) -> dict[str, str]:
    return {str(col): logical_type(df[col]) for col in df.columns}


@dataclass(frozen=True)
class Baseline:
    schema: dict[str, str]
    null_rates: dict[str, float]
    reference: pd.DataFrame
    expected_rows: int

    @property
    def numeric_columns(self) -> list[str]:
        return [c for c, t in self.schema.items() if t == NUMBER]

    @classmethod
    def from_frame(cls, df: pd.DataFrame, expected_rows: int) -> Baseline:
        return cls(
            schema=schema_of(df),
            null_rates={str(c): float(df[c].isna().mean()) for c in df.columns},
            reference=df,
            expected_rows=expected_rows,
        )


def read_csv(path: Path | str, datetime_columns: list[str] | None = None) -> pd.DataFrame:
    """Read a CSV and parse the datetime columns named in the contract."""
    df = pd.read_csv(path)
    for col in datetime_columns or []:
        if col in df.columns and logical_type(df[col]) == STRING:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def load_baseline(path: Path | str = DEFAULT_REFERENCE, expected_rows: int = 500) -> Baseline:
    raw = pd.read_csv(path)
    date_cols = [c for c in raw.columns if c.endswith("_datetime")]
    df = read_csv(path, date_cols)
    return Baseline.from_frame(df, expected_rows)


def datetime_columns(baseline: Baseline) -> list[str]:
    return [c for c, t in baseline.schema.items() if t == DATETIME]
