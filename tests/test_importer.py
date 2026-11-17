"""CSV import reports row-level errors without exposing personal data."""
from pathlib import Path
import httpx
import pytest
from leadflow_bridge.client import CRMClient
from leadflow_bridge.importer import sync_csv


def test_csv_import_counts_created_existing_and_invalid(tmp_path):
    path = tmp_path / "leads.csv"
    path.write_text("external_id,name,email,company,source\nA-1,Alex,alex@example.com,Demo,Web\nA-1,Alex,alex@example.com,Demo,Web\nA-2,Bad,bad-email,Demo,Web\nA-3,Sam,sam@example.com,Example,Form\n", encoding="utf-8")
    seen = set()
    def handler(request):
        key = request.headers["Idempotency-Key"]
        if key in seen:
            return httpx.Response(200, json={"created":False,"external_id":key})
        seen.add(key)
        return httpx.Response(201, json={"created":True,"external_id":key})
    with CRMClient("https://example.test/api/leads", token="t", transport=httpx.MockTransport(handler)) as client:
        report = sync_csv(path, client)
    assert report.to_dict()["summary"] == {"total_rows":4,"created":2,"already_exists":1,"invalid":1,"failed":0}
    assert report.to_dict()["issues"][0]["line"] == 4
    assert "bad-email" not in str(report.to_dict())


def test_csv_missing_headers_fails_before_any_network_call(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("email,name\na@example.com,Alex\n", encoding="utf-8")
    with CRMClient("https://example.test/api/leads", token="t", transport=httpx.MockTransport(lambda _: pytest.fail("must not send"))) as client:
        with pytest.raises(ValueError, match="Missing CSV columns"):
            sync_csv(path, client)


def test_api_failures_do_not_stop_processing_following_rows(tmp_path):
    path = tmp_path / "input.csv"
    path.write_text("external_id,name,email,company,source\nX-1,Alex,a@example.com,Demo,Web\nX-2,Sam,s@example.com,Demo,Web\n", encoding="utf-8")
    def handler(request):
        if request.headers["Idempotency-Key"] == "X-1":
            return httpx.Response(401, json={"detail":"bad creds"})
        return httpx.Response(201, json={"created":True,"external_id":"X-2"})
    with CRMClient("https://example.test/api/leads", token="t", transport=httpx.MockTransport(handler)) as client:
        report = sync_csv(path, client)
    assert report.to_dict()["summary"]["failed"] == 1
    assert report.to_dict()["summary"]["created"] == 1
    assert report.to_dict()["issues"][0]["line"] == 2
