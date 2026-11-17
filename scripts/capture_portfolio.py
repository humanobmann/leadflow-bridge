"""Capture the demo dashboard using verified local API data.

On an unrestricted computer this uses a real browser-to-API request. In a
restricted sandbox that blocks browser navigation, it uses a truthful local
HTTP response retrieved by Python and injects it for visual rendering.
The fallback is NOT an end-to-end browser network test.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "disposable-local-demo-token"


def available_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def capture(output: Path | None = None) -> Path:
    from playwright.sync_api import sync_playwright

    output = output or (ROOT / "assets" / "demo_dashboard.png")
    port = available_port()
    env = dict(os.environ, LEADFLOW_API_TOKEN=TOKEN)
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    with tempfile.TemporaryDirectory(prefix="leadflow_capture_") as tmpdir:
        process = subprocess.Popen([
            sys.executable, "-m", "leadflow_bridge.cli", "serve",
            "--db", str(Path(tmpdir) / "demo.sqlite"), "--port", str(port),
        ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=env)
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(80):
                if process.poll() is not None:
                    raise RuntimeError("Local API exited before readiness")
                try:
                    with urllib.request.urlopen(f"{base}/healthz", timeout=0.4) as response:
                        if json.load(response)["status"] == "ok":
                            break
                except (urllib.error.URLError, TimeoutError):
                    time.sleep(0.1)
            else:
                raise RuntimeError("Local CRM health check timed out")
            for pass_no, expected in [(1, 4), (2, 0)]:
                proc = subprocess.run([
                    sys.executable, "-m", "leadflow_bridge.cli", "sync",
                    str(ROOT / "examples" / "leads.csv"),
                    "--api-url", f"{base}/api/leads",
                ], env=env, capture_output=True, text=True, timeout=20, check=True)
                summary = json.loads(proc.stdout)["summary"]
                if summary["created"] != expected:
                    raise RuntimeError(f"Unexpected creation count in pass {pass_no}: {summary}")
            with sync_playwright() as playwright:
                system_chromium = shutil.which("chromium") or shutil.which("chromium-browser")
                browser = playwright.chromium.launch(
                    executable_path=system_chromium if system_chromium else None,
                    headless=True,
                    args=["--no-sandbox"] if os.name == "posix" and hasattr(os, "geteuid") and os.geteuid() == 0 else [],
                )
                try:
                    page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=1)
                    from playwright.sync_api import Error as PlaywrightError
                    capture_mode = "browser_live_local_http"
                    try:
                        page.goto(f"{base}/dashboard", wait_until="networkidle", timeout=8000)
                    except PlaywrightError as exc:
                        if "ERR_BLOCKED_BY_ADMINISTRATOR" not in str(exc):
                            raise
                        # Some managed environments block browser navigation to
                        # localhost. Get the REAL authenticated API response via
                        # Python and use it only to hydrate the captured UI.
                        capture_mode = "browser_render_with_verified_api_response"
                        request = urllib.request.Request(
                            f"{base}/api/leads?limit=1000",
                            headers={"Authorization": f"Bearer {TOKEN}"},
                        )
                        with urllib.request.urlopen(request, timeout=3) as result:
                            payload = json.load(result)
                        if payload["total"] != 4:
                            raise AssertionError("Dashboard evidence source must contain four records")
                        html = (ROOT / "src" / "leadflow_bridge" / "static" / "dashboard.html").read_text(encoding="utf-8")
                        # Discard the blocked-navigation page to avoid racing an
                        # error-page navigation against set_content.
                        page.close()
                        page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=1)
                        page.set_content(html, wait_until="load")
                        page.evaluate("payload => { window.fetch = async () => ({ok:true,json:async()=>payload}); }", payload)
                    page.get_by_label("Local demo token").fill(TOKEN)
                    page.get_by_role("button", name="Load data").click()
                    page.locator("#stat-count").get_by_text("4").wait_for(timeout=7000)
                    page.locator("#stat-http").get_by_text("200 OK").wait_for(timeout=7000)
                    if page.locator("#lead-rows tr").count() != 4:
                        raise AssertionError("Browser dashboard does not show exactly four live demo rows")
                    output.parent.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(output), full_page=False, animations="disabled")
                    print(f"Captured screenshot mode={capture_mode}: {output} ({output.stat().st_size} bytes)")
                finally:
                    browser.close()
            return output
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    capture()
