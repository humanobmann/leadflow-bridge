"""Cross-platform end-to-end demo using actual HTTP requests on loopback.

No external network calls, accounts, services, or real personal information.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL_TOKEN = "local-demo-example-token"  # Local-only disposable demo credential.


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def request_json(url: str, token: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=1) as r:
        return json.loads(r.read())


def run() -> dict:
    port = free_port()
    env = dict(os.environ, LEADFLOW_API_TOKEN=LOCAL_TOKEN)
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    with tempfile.TemporaryDirectory(prefix="leadflow_local_") as tmp:
        db = str(Path(tmp) / "crm.sqlite")
        proc = subprocess.Popen(
            [sys.executable, "-m", "leadflow_bridge.cli", "serve", "--db", db, "--port", str(port)],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        try:
            for _ in range(80):
                if proc.poll() is not None:
                    raise RuntimeError("Local CRM server exited before readiness")
                try:
                    if request_json(f"http://127.0.0.1:{port}/healthz") == {"status": "ok"}:
                        break
                except (urllib.error.URLError, TimeoutError):
                    time.sleep(0.1)
            else:
                raise RuntimeError("Local CRM server readiness timeout")

            results = []
            for pass_no in [1, 2]:
                command = [
                    sys.executable, "-m", "leadflow_bridge.cli", "sync",
                    str(ROOT / "examples" / "leads.csv"),
                    "--api-url", f"http://127.0.0.1:{port}/api/leads",
                ]
                process = subprocess.run(command, env=env, text=True, capture_output=True, timeout=20)
                if process.returncode != 0:
                    raise RuntimeError("Import subprocess failed: " + process.stderr[:400])
                result = json.loads(process.stdout)
                results.append(result["summary"])
                print(f"Import pass {pass_no}: {result['summary']}")

            leads = request_json(f"http://127.0.0.1:{port}/api/leads", token=LOCAL_TOKEN)
            if results[0] != {"total_rows":4,"created":4,"already_exists":0,"invalid":0,"failed":0}:
                raise AssertionError("First pass did not create exactly four leads")
            if results[1] != {"total_rows":4,"created":0,"already_exists":4,"invalid":0,"failed":0}:
                raise AssertionError("Second pass did not treat all as duplicates")
            if leads["count"] != 4:
                raise AssertionError("Database contains unexpected number of records")
            if not any(v["email"] == "taylor.brooks@example.com" for v in leads["leads"]):
                raise AssertionError("Email normalization not persisted")
            print("Verified: 4 persisted leads, normalization, duplicate-safe reimport")
            return {"environment":"local loopback only", "first_run":results[0], "second_run":results[1], "persisted_records":leads["count"], "normalization_verified":True, "api":"local demo REST API", "external_crm_connected":False}
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


if __name__ == "__main__":
    output = run()
    print(json.dumps(output, indent=2))
