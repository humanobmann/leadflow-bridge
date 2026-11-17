"""Strict CSV processing and privacy-preserving synchronization reports."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from .client import CRMClient, CRMError
from .models import Lead

REQUIRED_COLUMNS = {"external_id", "name", "email", "company", "source"}


@dataclass
class SyncReport:
    total_rows: int = 0
    created: int = 0
    already_exists: int = 0
    invalid: int = 0
    failed: int = 0
    issues: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total_rows": self.total_rows,
                "created": self.created,
                "already_exists": self.already_exists,
                "invalid": self.invalid,
                "failed": self.failed,
            },
            "issues": self.issues,
        }


def sync_csv(path: str | Path, client: CRMClient) -> SyncReport:
    """Continue after invalid rows and API errors, but reject bad file schemas."""
    report = SyncReport()
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        raw_headers = reader.fieldnames or []
        fieldnames = set(raw_headers)
        missing = sorted(REQUIRED_COLUMNS - fieldnames)
        if missing:
            raise ValueError("Missing CSV columns: " + ", ".join(missing))
        if len(raw_headers) != len(fieldnames) or fieldnames != REQUIRED_COLUMNS:
            # Reject ambiguous, duplicate and unexpected headers before any API call.
            # Do not echo unknown column labels, which might contain sensitive data.
            raise ValueError("CSV header contains duplicate or unexpected columns")
        for row in reader:
            line = reader.line_num
            report.total_rows += 1
            if None in row:
                report.invalid += 1
                report.issues.append({"line": line, "type": "invalid", "message": "Unexpected extra CSV columns"})
                continue
            try:
                lead = Lead.model_validate({name: row.get(name) for name in REQUIRED_COLUMNS})
            except ValidationError as exc:
                # Field names are safe to reveal, user-supplied values are not.
                fields = sorted({str(item["loc"][0]) for item in exc.errors() if item.get("loc")})
                report.invalid += 1
                report.issues.append({"line": line, "type": "invalid", "message": "Invalid field(s): " + ", ".join(fields)})
                continue
            try:
                created = client.post_lead(lead)
            except CRMError as exc:
                report.failed += 1
                report.issues.append({"line": line, "type": "api_error", "message": str(exc)})
                continue
            if created:
                report.created += 1
            else:
                report.already_exists += 1
    return report
