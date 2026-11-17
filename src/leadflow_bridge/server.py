"""A local, documented CRM-compatible REST endpoint backed by SQLite.

Important: this is a demo CRM, not a hosted integration with a third-party CRM.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from contextlib import contextmanager
from collections.abc import Iterator
import sqlite3
from importlib import resources
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Response, status, Query
from pydantic import BaseModel
from fastapi.responses import HTMLResponse

from .models import Lead


class LeadResult(BaseModel):
    external_id: str
    created: bool


def create_app(db_path: str | Path, api_token: str) -> FastAPI:
    """Create an independently testable app with a configured database and key."""
    if not api_token:
        raise ValueError("A non-empty API token is required")
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connection() -> Iterator[sqlite3.Connection]:
        """Commit or roll back the transaction, then always close the handle."""
        conn = sqlite3.connect(db_file, timeout=5)
        try:
            conn.row_factory = sqlite3.Row
            with conn:
                yield conn
        finally:
            conn.close()

    with connection() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS leads (
            external_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            company TEXT NOT NULL,
            source TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        )""")

    app = FastAPI(
        title="LeadFlow Bridge - Local Demo CRM API",
        description="Local reference CRM for reproducible CSV-to-REST-API integration testing.",
        version="2.0.0",
    )

    def authorize(authorization: str | None = Header(default=None)) -> None:
        prefix = "Bearer "
        if not authorization or not authorization.startswith(prefix):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        supplied = authorization[len(prefix):]
        if not hmac.compare_digest(supplied, api_token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    @app.get("/healthz", tags=["Diagnostics"])
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/leads", response_model=LeadResult, tags=["Leads"])
    def create_lead(
        lead: Lead,
        response: Response,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
        _: None = Depends(authorize),
    ):
        if idempotency_key != lead.external_id:
            raise HTTPException(status_code=400, detail="Idempotency-Key must equal external_id")
        fingerprint = hashlib.sha256(
            json.dumps(lead.model_dump(), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        ).hexdigest()
        with connection() as conn:
            inserted = conn.execute(
                """INSERT INTO leads (external_id, name, email, company, source, fingerprint)
                VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(external_id) DO NOTHING""",
                (lead.external_id, lead.name, lead.email, lead.company, lead.source, fingerprint),
            )
            created = inserted.rowcount == 1
            if not created:
                existing = conn.execute(
                    "SELECT fingerprint FROM leads WHERE external_id = ?", (lead.external_id,)
                ).fetchone()
                if existing is None or existing["fingerprint"] != fingerprint:
                    raise HTTPException(status_code=409, detail="Existing ID has different lead data")
        response.status_code = 201 if created else 200
        return LeadResult(external_id=lead.external_id, created=created)

    @app.get("/api/leads", tags=["Leads"])
    def list_leads(
        _: None = Depends(authorize),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> dict:
        """A bounded and deterministic page of local demo records."""
        with connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
            rows = conn.execute(
                "SELECT external_id, name, email, company, source, created_at "
                "FROM leads ORDER BY external_id LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return {"count": len(rows), "total": total, "leads": [dict(row) for row in rows]}

    @app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
    def dashboard() -> HTMLResponse:
        """Self-contained read-only demo UI; token supplied in browser memory only."""
        page = resources.files("leadflow_bridge").joinpath("static/dashboard.html").read_text(encoding="utf-8")
        return HTMLResponse(page, headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})

    return app
