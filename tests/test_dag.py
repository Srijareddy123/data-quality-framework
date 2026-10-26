import pytest

pytest.importorskip("airflow")


def test_dag_imports_without_errors():
    from airflow.models import DagBag

    bag = DagBag(dag_folder="dags", include_examples=False)
    assert not bag.import_errors
    assert "dq_validate_load" in bag.dags
