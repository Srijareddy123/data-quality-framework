import sys

from dqf import demo
from dqf.store import AuditStore, make_engine


def test_demo_runs_and_logs_every_load(tmp_path, monkeypatch, capsys):
    url = f"sqlite:///{tmp_path / 'demo.db'}"
    monkeypatch.setattr(sys, "argv", ["demo", "--db", url])
    demo.main()
    out = capsys.readouterr().out
    assert "audit log: 9 runs" in out
    runs = AuditStore(make_engine(url)).list_runs()
    statuses = {r["batch_id"]: r["status"] for r in runs}
    assert statuses["0 clean"] == "passed"
    assert statuses["3 nulls"] == "failed"
    assert statuses["6 value_drift"] == "warning"
