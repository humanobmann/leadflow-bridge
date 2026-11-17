"""Contract checks for the demo CRM API, including idempotency."""
import pytest
from fastapi.testclient import TestClient
from leadflow_bridge.server import create_app

TOKEN = "test-token-for-local-demo"

@pytest.fixture
def api(tmp_path):
    with TestClient(create_app(tmp_path / "crm.sqlite", TOKEN)) as c:
        yield c

@pytest.fixture
def headers():
    return {"Authorization": f"Bearer {TOKEN}", "Idempotency-Key": "DEMO-1"}

@pytest.fixture
def payload():
    return {"external_id": "DEMO-1", "name": "Alex Rivera", "email": " ALEX@EXAMPLE.COM ", "company": "Example Labs", "source": "Website"}


def test_authenticated_post_persists_normalized_lead(api, headers, payload):
    response = api.post("/api/leads", json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json() == {"external_id": "DEMO-1", "created": True}
    listing = api.get("/api/leads", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["count"] == 1
    assert listing.json()["leads"][0]["email"] == "alex@example.com"


def test_exact_duplicate_is_idempotent_and_conflicting_payload_rejected(api, headers, payload):
    assert api.post("/api/leads", json=payload, headers=headers).status_code == 201
    assert api.post("/api/leads", json=payload, headers=headers).json()["created"] is False
    different = {**payload, "company": "A different company"}
    assert api.post("/api/leads", json=different, headers=headers).status_code == 409
    assert api.get("/api/leads", headers=headers).json()["count"] == 1


def test_api_requires_token_and_matching_idempotency_key(api, headers, payload):
    assert api.get("/api/leads").status_code == 401
    assert api.post("/api/leads", json=payload).status_code == 401
    bad_headers = {**headers, "Idempotency-Key": "OTHER"}
    assert api.post("/api/leads", json=payload, headers=bad_headers).status_code == 400
    assert api.get("/api/leads", headers=headers).json()["count"] == 0


def test_invalid_email_and_extra_fields_are_rejected(api, headers, payload):
    assert api.post("/api/leads", json={**payload, "email": "not-an-email"}, headers=headers).status_code == 422
    assert api.post("/api/leads", json={**payload, "secret": "unused"}, headers=headers).status_code == 422


def test_health_endpoint_is_safe_and_accessible(api):
    response = api.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
