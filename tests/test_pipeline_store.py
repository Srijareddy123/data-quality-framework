import pytest

from dqf.loads import get_load
from dqf.pipeline import run_validation

DATASET = "taxi"


def test_run_is_written_to_the_audit_log(pool, baseline, store):
    run_id, status, found = run_validation(
        get_load(pool, 3, "nulls"), baseline, store, DATASET, "3 nulls"
    )
    run = store.get_run(run_id)
    assert run["status"] == status == "failed"
    assert run["row_count"] == 500
    assert [f["check_name"] for f in run["findings"]] == [f.check for f in found]
    assert store.counts() == {"runs": 1, "findings": len(found)}


def test_alerts_can_be_filtered(pool, baseline, store):
    run_validation(get_load(pool, 3, "nulls"), baseline, store, DATASET, "a")
    run_validation(get_load(pool, 6, "value_drift"), baseline, store, DATASET, "b")
    assert {a["check_name"] for a in store.list_alerts(severity="warning")} == {"value_drift"}
    assert {a["check_name"] for a in store.list_alerts(check="nulls")} == {"nulls"}
    assert len(store.list_alerts(limit=1)) == 1


def test_bad_schema_is_not_used_as_the_next_reference(pool, baseline, store):
    run_validation(get_load(pool, 0), baseline, store, DATASET, "ok")
    good = store.latest_schema(DATASET)
    run_validation(get_load(pool, 1, "schema_change"), baseline, store, DATASET, "bad")
    assert store.latest_schema(DATASET) == good
    _, status, found = run_validation(get_load(pool, 2), baseline, store, DATASET, "ok again")
    assert status == "passed" and found == []


def test_unknown_run_returns_none(store):
    assert store.get_run(999) is None


def test_unknown_defect_is_rejected(pool):
    with pytest.raises(ValueError):
        get_load(pool, 0, "gremlins")
