"""Regression tests for CSV parsing, bounded retry policy, and public demo UI."""
from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from leadflow_bridge.client import CRMClient
from leadflow_bridge.importer import sync_csv
from leadflow_bridge.models import Lead
from leadflow_bridge.server import create_app


@pytest.mark.parametrize('header', [
    'external_id,name,email,company,source,email',
    'external_id,name,email,company,source,password',
    'external_id,name,email,company,source,',
])
def test_csv_rejects_ambiguous_or_unexpected_header_before_network(tmp_path, header):
    csv_file = tmp_path / 'input.csv'
    csv_file.write_text(header + '\nID-001,Alex,alex@example.com,Demo,Web\n', encoding='utf-8')
    with CRMClient('https://example.test/api/leads', 'demo', transport=httpx.MockTransport(
        lambda request: pytest.fail('Rejected CSV must never reach the network')
    )) as client:
        with pytest.raises(ValueError, match='CSV header'):
            sync_csv(csv_file, client)


def test_retry_after_nan_falls_back_to_safe_delay():
    attempts, delays = [], []

    def handler(request):
        attempts.append(1)
        if len(attempts) == 1:
            return httpx.Response(429, headers={'Retry-After': 'nan'})
        return httpx.Response(201, json={'created': True, 'external_id': 'TEST-1'})

    with CRMClient('https://example.test/api/leads', 'demo', max_retries=1,
                   transport=httpx.MockTransport(handler), sleep=delays.append) as client:
        assert client.post_lead(Lead(external_id='TEST-1', name='Alex Demo',
                                     email='alex@example.com', company='Test', source='Web'))
    assert attempts == [1, 1]
    assert delays == [0.2]


def test_list_api_uses_bounded_pagination(tmp_path):
    api = TestClient(create_app(tmp_path / 'leads.db', 'test-token'))
    base_headers = {'Authorization': 'Bearer test-token'}
    for i in range(3):
        payload = {'external_id': f'ID-{i}', 'name': 'Alex Demo',
                   'email': f'alex{i}@example.com', 'company': 'Demo', 'source': 'Web'}
        response = api.post('/api/leads', headers={**base_headers, 'Idempotency-Key': f'ID-{i}'}, json=payload)
        assert response.status_code == 201
    response = api.get('/api/leads?limit=2&offset=1', headers=base_headers)
    assert response.status_code == 200
    assert response.json()['count'] == 2
    assert response.json()['total'] == 3
    assert [x['external_id'] for x in response.json()['leads']] == ['ID-1', 'ID-2']
    assert api.get('/api/leads?limit=1001', headers=base_headers).status_code == 422
    assert api.get('/api/leads?offset=-1', headers=base_headers).status_code == 422


def test_dashboard_is_local_read_only_ui_not_embedded_token(tmp_path):
    api = TestClient(create_app(tmp_path / 'leads.db', 'super-secret-do-not-render'))
    page = api.get('/dashboard')
    assert page.status_code == 200
    assert 'LeadFlow' in page.text
    assert 'Connect to local demo' in page.text
    assert '/api/leads' in page.text
    assert 'super-secret-do-not-render' not in page.text
    assert '<script' in page.text


def test_database_connections_are_closed_after_transactions(tmp_path, monkeypatch):
    """Connections must be closed, not merely committed by sqlite3's context manager."""
    import sqlite3
    import leadflow_bridge.server as server_module

    actual_connect = sqlite3.connect
    opened = []

    class TrackingConnection(sqlite3.Connection):
        closed_on_exit = False

        def close(self):
            self.closed_on_exit = True
            return super().close()

    def tracked_connect(*args, **kwargs):
        result = actual_connect(*args, factory=TrackingConnection, **kwargs)
        opened.append(result)
        return result

    monkeypatch.setattr(server_module.sqlite3, 'connect', tracked_connect)
    client = TestClient(create_app(tmp_path / 'leads.db', 'test-token'))
    token = {'Authorization': 'Bearer test-token', 'Idempotency-Key': 'ID-CLOSE'}
    payload = {'external_id': 'ID-CLOSE', 'name': 'Alex Demo',
               'email': 'alex@example.com', 'company': 'Demo', 'source': 'Web'}
    assert client.post('/api/leads', json=payload, headers=token).status_code == 201
    assert client.get('/api/leads', headers=token).status_code == 200
    assert len(opened) >= 3
    assert all(conn.closed_on_exit for conn in opened), 'SQLite connections were not explicitly closed'
