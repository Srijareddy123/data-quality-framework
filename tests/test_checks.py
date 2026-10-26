import numpy as np

from dqf import findings as fk
from dqf.inject import inject_nulls, inject_row_loss, inject_schema_change, inject_value_drift
from dqf.pipeline import FAILED, PASSED, WARNED, status_of, validate_load


def checks_of(found):
    return {f.check for f in found}


def test_clean_load_has_no_findings(clean, baseline):
    assert validate_load(clean, baseline) == []
    assert status_of([]) == PASSED


def test_heavy_nulls_are_flagged_on_the_right_column(clean, baseline):
    bad = inject_nulls(clean, np.random.default_rng(1), "fare_amount", 0.2)
    found = validate_load(bad, baseline)
    assert [(f.check, f.column) for f in found] == [(fk.NULLS, "fare_amount")]
    assert status_of(found) == FAILED


def test_nulls_within_the_baseline_rate_are_not_flagged(clean, baseline):
    # passenger_count is already null about 5 percent of the time in the real data
    assert baseline.null_rates["passenger_count"] > 0.02
    ok = inject_nulls(clean, np.random.default_rng(1), "tip_amount", 0.0)
    assert validate_load(ok, baseline) == []


def test_row_loss_is_flagged_but_small_loss_is_not(clean, baseline):
    rng = np.random.default_rng(2)
    assert checks_of(validate_load(inject_row_loss(clean, rng, 0.2), baseline)) == {fk.ROW_COUNT}
    assert validate_load(inject_row_loss(clean, rng, 0.9), baseline) == []


def test_empty_load_does_not_crash(clean, baseline):
    found = validate_load(clean.iloc[0:0], baseline)
    assert fk.ROW_COUNT in checks_of(found)


def test_each_schema_change_is_caught_by_conformance_and_drift(clean, baseline):
    for kind in ("drop_column", "rename_column", "add_column", "retype_column"):
        bad = inject_schema_change(clean, np.random.default_rng(3), kind)
        assert {fk.SCHEMA_DRIFT, fk.SCHEMA_CONFORMANCE} <= checks_of(
            validate_load(bad, baseline)
        ), kind


def test_schema_drift_message_names_the_change(clean, baseline):
    bad = clean.drop(columns=["tip_amount"])
    drift = [f for f in validate_load(bad, baseline) if f.check == fk.SCHEMA_DRIFT]
    assert drift[0].message == "column removed: tip_amount"


def test_value_drift_is_a_warning_on_the_shifted_column(clean, baseline):
    bad = inject_value_drift(clean, "trip_distance", 0.5)
    found = validate_load(bad, baseline)
    assert [(f.check, f.column) for f in found] == [(fk.VALUE_DRIFT, "trip_distance")]
    assert status_of(found) == WARNED


def test_injectors_do_not_change_their_input(clean):
    before = clean.copy()
    rng = np.random.default_rng(4)
    inject_nulls(clean, rng, "fare_amount", 0.5)
    inject_row_loss(clean, rng, 0.5)
    inject_schema_change(clean, rng, "retype_column")
    inject_value_drift(clean, "fare_amount", 1.0)
    assert clean.equals(before)


def test_retyped_column_message_names_both_types(clean, baseline):
    bad = clean.copy()
    bad["fare_amount"] = bad["fare_amount"].astype(str)
    msgs = {f.message for f in validate_load(bad, baseline) if f.check == fk.SCHEMA_CONFORMANCE}
    assert msgs == {"type string, contract says number"}
