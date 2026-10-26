"""One result of one check on one load."""

from __future__ import annotations

from dataclasses import dataclass

ROW_COUNT = "row_count"
NULLS = "nulls"
SCHEMA_CONFORMANCE = "schema_conformance"
SCHEMA_DRIFT = "schema_drift"
VALUE_DRIFT = "value_drift"

ERROR, WARNING = "error", "warning"


@dataclass(frozen=True)
class Finding:
    check: str
    severity: str
    message: str
    column: str | None = None
