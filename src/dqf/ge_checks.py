"""Row count, null and schema conformance checks, run as a Great Expectations suite."""

from __future__ import annotations

import math
from functools import lru_cache

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd
from great_expectations.data_context.types.base import ProgressBarsConfig

from dqf.baseline import BOOLEAN, DATETIME, NUMBER, STRING, Baseline, schema_of
from dqf.findings import ERROR, NULLS, ROW_COUNT, SCHEMA_CONFORMANCE, Finding

ROW_COUNT_TOLERANCE = 0.4  # a load may be 40 percent smaller or larger than expected
NULL_BASE_TOLERANCE = 0.01  # extra null rate allowed on top of the baseline
NULL_SIGMAS = 4  # plus this many standard errors of the baseline rate

TYPE_NAMES = {
    NUMBER: [
        "int8",
        "int16",
        "int32",
        "int64",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
        "float32",
        "float64",
    ],
    STRING: ["str", "object", "string"],
    DATETIME: ["datetime64[ns]", "datetime64[us]", "datetime64[ms]", "datetime64[s]"],
    BOOLEAN: ["bool", "boolean"],
}


@lru_cache(maxsize=1)
def _batch_definition():
    context = gx.get_context(mode="ephemeral")
    context.variables.progress_bars = ProgressBarsConfig(globally=False, metric_calculations=False)
    source = context.data_sources.add_pandas("loads")
    asset = source.add_dataframe_asset("load")
    return asset.add_batch_definition_whole_dataframe("whole")


def null_limit(base_rate: float, rows: int) -> float:
    """Highest null rate we accept for a column, given its baseline rate and the load size."""
    std_err = math.sqrt(base_rate * (1 - base_rate) / max(rows, 1))
    return min(1.0, base_rate + NULL_BASE_TOLERANCE + NULL_SIGMAS * std_err)


def build_suite(baseline: Baseline, present: set[str]) -> gx.ExpectationSuite:
    lo = math.floor(baseline.expected_rows * (1 - ROW_COUNT_TOLERANCE))
    hi = math.ceil(baseline.expected_rows * (1 + ROW_COUNT_TOLERANCE))
    suite = gx.ExpectationSuite(name="load_contract")
    suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=lo, max_value=hi))
    suite.add_expectation(
        gxe.ExpectTableColumnsToMatchSet(column_set=list(baseline.schema), exact_match=True)
    )
    for col, logical in baseline.schema.items():
        if col not in present:
            continue
        suite.add_expectation(
            gxe.ExpectColumnValuesToBeInTypeList(column=col, type_list=TYPE_NAMES[logical])
        )
    return suite


def _null_suite(baseline: Baseline, present: set[str], rows: int) -> gx.ExpectationSuite:
    suite = gx.ExpectationSuite(name="null_limits")
    for col in baseline.schema:
        if col in present:
            mostly = 1 - null_limit(baseline.null_rates[col], rows)
            suite.add_expectation(
                gxe.ExpectColumnValuesToNotBeNull(column=col, mostly=max(mostly, 0.0))
            )
    return suite


def _run(df: pd.DataFrame, suite: gx.ExpectationSuite):
    batch = _batch_definition().get_batch(batch_parameters={"dataframe": df})
    return batch.validate(suite)


def run_ge_checks(df: pd.DataFrame, baseline: Baseline) -> list[Finding]:
    _batch_definition()  # makes sure the GX context exists before suites are built
    present = {str(c) for c in df.columns}
    findings: list[Finding] = []
    for res in _run(df, build_suite(baseline, present)).results:
        if res.success:
            continue
        cfg = res.expectation_config
        observed = res.result.get("observed_value")
        if cfg.type == "expect_table_row_count_to_be_between":
            msg = (
                f"{observed} rows, expected {cfg.kwargs['min_value']} to {cfg.kwargs['max_value']}"
            )
            findings.append(Finding(ROW_COUNT, ERROR, msg))
        elif cfg.type == "expect_table_columns_to_match_set":
            missing = sorted(set(baseline.schema) - present)
            extra = sorted(present - set(baseline.schema))
            findings.append(
                Finding(SCHEMA_CONFORMANCE, ERROR, f"missing columns {missing}, unexpected {extra}")
            )
        else:
            col = cfg.kwargs["column"]
            msg = f"type {schema_of(df)[col]}, contract says {baseline.schema[col]}"
            findings.append(Finding(SCHEMA_CONFORMANCE, ERROR, msg, col))
    if len(df) == 0:
        return findings
    for res in _run(df, _null_suite(baseline, present, len(df))).results:
        if not res.success:
            col = res.expectation_config.kwargs["column"]
            rate = res.result["unexpected_percent"] / 100
            limit = null_limit(baseline.null_rates[col], len(df))
            findings.append(Finding(NULLS, ERROR, f"null rate {rate:.1%}, limit {limit:.1%}", col))
    return findings
