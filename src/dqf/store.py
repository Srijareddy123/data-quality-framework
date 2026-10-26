"""PostgreSQL (or SQLite in tests) audit log: every run, every finding, every schema seen.

A schema counts as accepted when the load matched the contract. Drift is measured
against the last accepted schema, so one bad load does not hide the next one.

Written with SQLAlchemy Core in a style that works on 1.4 and 2.x, because the
Airflow image pins 1.4.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    desc,
    func,
    insert,
    select,
    text,
)
from sqlalchemy.engine import Engine

DEFAULT_URL = "sqlite:///dqf_audit.db"

metadata = MetaData()

runs = Table(
    "dq_runs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("dataset", String(100), nullable=False),
    Column("batch_id", String(100), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("row_count", Integer, nullable=False),
    Column("status", String(20), nullable=False),
    Column("finding_count", Integer, nullable=False),
)
findings = Table(
    "dq_findings",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("run_id", Integer, ForeignKey("dq_runs.id"), nullable=False, index=True),
    Column("check_name", String(50), nullable=False),
    Column("severity", String(20), nullable=False),
    Column("column_name", String(100)),
    Column("message", String(500), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
schema_snapshots = Table(
    "dq_schema_snapshots",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("run_id", Integer, ForeignKey("dq_runs.id"), nullable=False),
    Column("dataset", String(100), nullable=False, index=True),
    Column("schema", JSON, nullable=False),
    Column("accepted", Boolean, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)


def make_engine(url: str | None = None) -> Engine:
    return create_engine(url or os.environ.get("DATABASE_URL", DEFAULT_URL), future=True)


class AuditStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        metadata.create_all(engine)

    def latest_schema(self, dataset: str) -> dict[str, str] | None:
        query = (
            select(schema_snapshots.c.schema)
            .where(schema_snapshots.c.dataset == dataset)
            .where(schema_snapshots.c.accepted.is_(True))
            .order_by(desc(schema_snapshots.c.id))
            .limit(1)
        )
        with self.engine.connect() as conn:
            row = conn.execute(query).first()
        return dict(row[0]) if row else None

    def record_run(
        self,
        dataset: str,
        batch_id: str,
        row_count: int,
        status: str,
        found: list[Any],
        schema: dict[str, str],
    ) -> int:
        now = datetime.now(UTC)
        with self.engine.begin() as conn:
            result = conn.execute(
                insert(runs).values(
                    dataset=dataset,
                    batch_id=batch_id,
                    started_at=now,
                    row_count=row_count,
                    status=status,
                    finding_count=len(found),
                )
            )
            run_id = int(result.inserted_primary_key[0])
            for f in found:
                conn.execute(
                    insert(findings).values(
                        run_id=run_id,
                        check_name=f.check,
                        severity=f.severity,
                        column_name=f.column,
                        message=f.message[:500],
                        created_at=now,
                    )
                )
            conn.execute(
                insert(schema_snapshots).values(
                    run_id=run_id,
                    dataset=dataset,
                    schema=schema,
                    created_at=now,
                    accepted=not any(f.check == "schema_conformance" for f in found),
                )
            )
        return run_id

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        query = select(runs).order_by(desc(runs.c.id)).limit(limit)
        with self.engine.connect() as conn:
            return [_row(r) for r in conn.execute(query)]

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        with self.engine.connect() as conn:
            row = conn.execute(select(runs).where(runs.c.id == run_id)).first()
            if row is None:
                return None
            out = _row(row)
            query = select(findings).where(findings.c.run_id == run_id).order_by(findings.c.id)
            out["findings"] = [_row(r) for r in conn.execute(query)]
        return out

    def list_alerts(
        self, severity: str | None = None, check: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        query = (
            select(findings, runs.c.dataset, runs.c.batch_id)
            .join(runs, runs.c.id == findings.c.run_id)
            .order_by(desc(findings.c.id))
            .limit(limit)
        )
        if severity:
            query = query.where(findings.c.severity == severity)
        if check:
            query = query.where(findings.c.check_name == check)
        with self.engine.connect() as conn:
            return [_row(r) for r in conn.execute(query)]

    def counts(self) -> dict[str, int]:
        with self.engine.connect() as conn:
            n_runs = conn.execute(select(func.count()).select_from(runs)).scalar_one()
            n_find = conn.execute(select(func.count()).select_from(findings)).scalar_one()
        return {"runs": int(n_runs), "findings": int(n_find)}

    def ping(self) -> None:
        with self.engine.connect() as conn:
            conn.execute(text("SELECT 1"))


def _row(row: Any) -> dict[str, Any]:
    out = dict(row._mapping)
    for key, value in out.items():
        if isinstance(value, datetime):
            out[key] = value.isoformat()
    return out
