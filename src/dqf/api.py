"""Health and alert endpoints over the audit log."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError

from dqf import __version__
from dqf.store import AuditStore, make_engine


def create_app(store: AuditStore | None = None) -> FastAPI:
    app = FastAPI(title="Data Quality Framework", version=__version__)
    holder: dict[str, AuditStore] = {}

    def get_store() -> AuditStore:
        if store is not None:
            return store
        if "store" not in holder:
            holder["store"] = AuditStore(make_engine())
        return holder["store"]

    @app.get("/health")
    def health() -> dict[str, Any]:
        try:
            s = get_store()
            s.ping()
            latest = s.list_runs(limit=1)
            counts = s.counts()
        except SQLAlchemyError as exc:
            raise HTTPException(
                status_code=503, detail=f"database unreachable: {exc.__class__.__name__}"
            ) from exc
        return {
            "status": "ok",
            "database": "ok",
            "runs": counts["runs"],
            "findings": counts["findings"],
            "last_run": latest[0] if latest else None,
        }

    @app.get("/alerts")
    def alerts(
        severity: str | None = Query(None, pattern="^(error|warning)$"),
        check: str | None = None,
        limit: int = Query(100, ge=1, le=1000),
    ) -> list[dict[str, Any]]:
        return get_store().list_alerts(severity=severity, check=check, limit=limit)

    @app.get("/runs")
    def list_runs(limit: int = Query(50, ge=1, le=500)) -> list[dict[str, Any]]:
        return get_store().list_runs(limit=limit)

    @app.get("/runs/{run_id}")
    def get_run(run_id: int) -> dict[str, Any]:
        run = get_store().get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        return run

    return app


app = create_app()
