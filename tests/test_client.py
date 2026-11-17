"""HTTP boundary retry policy and secure failures."""
import httpx
import pytest
from leadflow_bridge.client import CRMClient, CRMError
from leadflow_bridge.models import Lead

LEAD = {"external_id":"DEMO-2", "name":"Taylor Brooks", "email":"taylor@example.com", "company":"Demo Co", "source":"Event"}


def test_client_retries_retriable_503_and_succeeds_without_leaking_token():
    statuses = [503, 503, 201]
    calls = []
    delays = []
    def handler(request):
        calls.append(request)
        assert request.headers["Authorization"] == "Bearer sensitive-token"
        assert request.headers["Idempotency-Key"] == "DEMO-2"
        status = statuses.pop(0)
        return httpx.Response(status, json={"created": True, "external_id": "DEMO-2"} if status == 201 else {"detail": "temporary"})
    with CRMClient("https://example.test/api/leads", token="sensitive-token", transport=httpx.MockTransport(handler), max_retries=2, sleep=delays.append) as client:
        assert client.post_lead(Lead.model_validate(LEAD)) is True
    assert len(calls) == 3
    assert delays == [0.2, 0.4]


def test_client_does_not_retry_unauthorized_or_show_secret():
    calls = []
    def handler(request):
        calls.append(1)
        return httpx.Response(401, json={"detail":"invalid token"})
    with CRMClient("https://example.test/api/leads", token="secret-needle", transport=httpx.MockTransport(handler), max_retries=3, sleep=lambda _: None) as client:
        with pytest.raises(CRMError, match="401") as exc:
            client.post_lead(Lead.model_validate(LEAD))
    assert "secret-needle" not in str(exc.value)
    assert len(calls) == 1


def test_client_retries_transport_failures_and_aborts_at_limit():
    calls = []
    def handler(request):
        calls.append(1)
        raise httpx.ConnectError("network unavailable")
    with CRMClient("https://example.test/api/leads", token="secret-needle", transport=httpx.MockTransport(handler), max_retries=1, sleep=lambda _: None) as client:
        with pytest.raises(CRMError, match="Network error") as exc:
            client.post_lead(Lead.model_validate(LEAD))
    assert len(calls) == 2
    assert "secret-needle" not in str(exc.value)


def test_client_interprets_200_as_existing_and_409_as_conflict():
    response = httpx.MockTransport(lambda _: httpx.Response(200, json={"created":False,"external_id":"DEMO-2"}))
    with CRMClient("https://example.test/api/leads", token="t", transport=response) as client:
        assert client.post_lead(Lead.model_validate(LEAD)) is False
    conflict = httpx.MockTransport(lambda _: httpx.Response(409, json={"detail":"conflict"}))
    with CRMClient("https://example.test/api/leads", token="t", transport=conflict) as client:
        with pytest.raises(CRMError, match="409"):
            client.post_lead(Lead.model_validate(LEAD))
