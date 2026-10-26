import pytest

from dqf.evaluate import run_eval, to_markdown, wilson


def test_wilson_interval_bounds():
    lo, hi = wilson(10, 10)
    assert hi == 1.0 and 0.6 < lo < 0.8
    assert wilson(0, 0) == (0.0, 0.0)
    lo, hi = wilson(50, 100)
    assert lo < 0.5 < hi


@pytest.fixture(scope="module")
def result(baseline, pool):
    return run_eval(trials=4, seed=1, baseline=baseline, pool=pool)


def test_eval_is_reproducible(baseline, pool, result):
    again = run_eval(trials=4, seed=1, baseline=baseline, pool=pool)
    assert again["scenarios"] == result["scenarios"]


def test_obvious_defects_are_always_detected_and_clean_loads_stay_quiet(result):
    by_level = {(r["defect"], r["level"]): r for r in result["scenarios"]}
    assert by_level[("nulls", "30% of one column")]["detected"] == 4
    assert by_level[("schema_change", "drop_column")]["detected"] == 4
    assert by_level[("row_loss", "10% of rows kept")]["detected"] == 4
    assert all(r["false_positives"] == 0 for r in result["scenarios"])


def test_markdown_table_has_a_row_per_scenario(result):
    md = to_markdown(result)
    assert md.count("\n| ") == len(result["scenarios"]) + 1
    assert "python -m dqf.evaluate --trials 4 --seed 1" in md
