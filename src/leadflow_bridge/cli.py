"""CLI entry point for the local CRM and CSV integration."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import uvicorn

from .client import CRMClient
from .importer import sync_csv
from .server import create_app

DEFAULT_API_URL = "http://127.0.0.1:8765/api/leads"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="leadflow", description="Local, reproducible CSV to REST CRM API demo"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="Run local demonstration CRM API")
    serve.add_argument("--db", default="demo_crm.sqlite", help="SQLite file to store local demo records")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--host", default="127.0.0.1", choices=["127.0.0.1", "localhost"])
    sync = sub.add_parser("sync", help="Validate and send a CSV file to the API")
    sync.add_argument("csv_path", type=Path)
    sync.add_argument("--api-url", default=DEFAULT_API_URL)
    sync.add_argument("--report", type=Path, help="Optional path for JSON report")
    sync.add_argument("--retries", type=int, default=2)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    token = os.environ.get("LEADFLOW_API_TOKEN", "")
    if not token:
        print("Set LEADFLOW_API_TOKEN in your environment first.", file=sys.stderr)
        return 2

    if args.command == "serve":
        try:
            app = create_app(args.db, token)
            uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
        except (ValueError, OSError) as exc:
            print(f"Cannot start server: {type(exc).__name__}", file=sys.stderr)
            return 2
        return 0

    try:
        with CRMClient(args.api_url, token, max_retries=args.retries) as client:
            report = sync_csv(args.csv_path, client)
        data = report.to_dict()
        output = json.dumps(data, indent=2, ensure_ascii=False)
        print(output)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(output + "\n", encoding="utf-8")
        return 2 if data["summary"]["invalid"] or data["summary"]["failed"] else 0
    except (OSError, ValueError) as exc:
        # No full exception bodies to prevent accidental disclosure of CSV contents.
        print(f"Import cannot start: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
