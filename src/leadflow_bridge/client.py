"""Small, testable REST integration client with bounded retries."""
from __future__ import annotations

import time
import math
from collections.abc import Callable
from urllib.parse import urlparse

import httpx

from .models import Lead


class CRMError(RuntimeError):
    """Sanitized failure description (never contains authorization headers)."""


RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


class CRMClient:
    """Send leads to the documented LeadFlow-compatible HTTP contract.

    Adapter boundaries are explicit: third-party CRMs require field/endpoint mapping.
    """

    def __init__(
        self,
        url: str,
        token: str,
        *,
        max_retries: int = 2,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("The API URL must be an absolute HTTP(S) URL")
        if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Use HTTPS for non-local API endpoints")
        if not token.strip():
            raise ValueError("API token must be non-empty")
        if not (0 <= max_retries <= 6):
            raise ValueError("max_retries must be between 0 and 6")
        self.url = url
        self._token = token
        self._retries = max_retries
        self._sleep = sleep
        self._client = httpx.Client(timeout=timeout_seconds, transport=transport, follow_redirects=False, trust_env=False)

    def __enter__(self) -> CRMClient:
        return self

    def __exit__(self, *_: object) -> None:
        self._client.close()

    def post_lead(self, lead: Lead) -> bool:
        """Return True if created, False if already present with identical content."""
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Idempotency-Key": lead.external_id,
            "Accept": "application/json",
        }
        for attempt in range(self._retries + 1):
            try:
                response = self._client.post(self.url, headers=headers, json=lead.model_dump())
            except httpx.RequestError:
                if attempt == self._retries:
                    raise CRMError("Network error; retry limit reached") from None
                self._sleep(min(0.2 * 2**attempt, 5.0))
                continue
            if response.status_code in (200, 201):
                try:
                    data = response.json()
                    created = data["created"]
                    identifier = data["external_id"]
                except (ValueError, KeyError, TypeError):
                    raise CRMError("Unexpected API response") from None
                if type(created) is not bool or identifier != lead.external_id:
                    raise CRMError("Unexpected API response")
                if created != (response.status_code == 201):
                    raise CRMError("Inconsistent API response status")
                return created
            if response.status_code in RETRYABLE_STATUSES and attempt < self._retries:
                retry_after = response.headers.get("Retry-After", "")
                try:
                    proposed_delay = float(retry_after)
                    if not math.isfinite(proposed_delay):
                        raise ValueError("Non-finite Retry-After")
                    delay = min(max(proposed_delay, 0.0), 5.0)
                except (ValueError, OverflowError):
                    delay = min(0.2 * 2**attempt, 5.0)
                self._sleep(delay)
                continue
            raise CRMError(f"CRM API returned HTTP {response.status_code}")
        raise CRMError("Request could not be completed")
