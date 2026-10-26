from fastapi.testclient import TestClient

from dqf.api import create_app
from dqf.loads import get_load
from dqf.pipeline import run_validation


def test_health_on_empty_log(store):
    body = TestClient(create_app(store)).get("/health").json()
    assert body["status"] == "ok" and body["runs"] == 0 and body["last_run"] is None


def test_alerts_and_runs_after_a_bad_load(pool, baseline, store):
    run_id, _, _ = run_validation(get_load(pool, 3, "nulls"), baseline, store, "taxi", "3 nulls")
    client = TestClient(create_app(store))

    health = client.get("/health").json()
    assert health["findings"] == 1 and health["last_run"]["status"] == "failed"

    alerts = client.get("/alerts", params={"severity": "error"}).json()
    assert alerts[0]["check_name"] == "nulls" and alerts[0]["column_name"] == "fare_amount"
    assert client.get("/alerts", params={"check": "row_count"}).json() == []

    assert client.get("/runs").json()[0]["id"] == run_id
    assert client.get(f"/runs/{run_id}").json()["findings"][0]["check_name"] == "nulls"


def test_bad_inputs_get_clear_errors(store):
    client = TestClient(create_app(store))
    assert client.get("/runs/12345").status_code == 404
    assert client.get("/alerts", params={"severity": "loud"}).status_code == 422


def test_health_reports_503_when_database_is_down(store, monkeypatch):
    from sqlalchemy.exc import OperationalError

    def boom():
        raise OperationalError("SELECT 1", {}, Exception("down"))

    monkeypatch.setattr(store, "ping", boom)
    resp = TestClient(create_app(store)).get("/health")
    assert resp.status_code == 503
    assert "OperationalError" in resp.json()["detail"]
