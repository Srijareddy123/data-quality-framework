"""Airflow DAG: validate one load. Trigger it once per load, for example from the
last task of the upstream pipeline, or by hand:

    airflow dags trigger dq_validate_load --conf '{"batch_index": 3, "defect": "nulls"}'
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.models.param import Param

DEFECTS = ["nulls", "schema_change", "value_drift", "row_loss"]


@dag(
    dag_id="dq_validate_load",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(seconds=10)},
    params={
        "batch_index": Param(0, type="integer", minimum=0),
        "defect": Param(None, type=["null", "string"], enum=[None, *DEFECTS]),
    },
    tags=["data-quality"],
)
def dq_validate_load():
    @task
    def validate(params: dict | None = None) -> dict:
        from dqf.baseline import load_baseline
        from dqf.loads import BATCH_ROWS, get_load, load_pool
        from dqf.pipeline import run_validation
        from dqf.store import AuditStore, make_engine

        params = params or {}
        index = int(params.get("batch_index", 0))
        defect = params.get("defect")
        baseline = load_baseline(expected_rows=BATCH_ROWS)
        df = get_load(load_pool(baseline), index, defect)
        store = AuditStore(make_engine())
        label = f"{index} {defect or 'clean'}"
        run_id, status, found = run_validation(df, baseline, store, "nyc_taxi_yellow", label)
        return {"run_id": run_id, "status": status, "findings": len(found)}

    validate()


dq_validate_load()
