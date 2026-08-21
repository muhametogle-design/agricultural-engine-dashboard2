"""Shared resilient HTTP plumbing for external geospatial APIs.

One AsyncClient is created at app startup (connection pooling, keep-alive)
and injected into every service call. Retries target transient failures only:
connection errors, 429 and 5xx. Deterministic 4xx fail fast.
"""
from __future__ import annotations

from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.config import HttpSettings
from app.core.errors import ExternalServiceError
from app.core.logging import get_logger

log = get_logger(__name__)


class _RetryableStatus(Exception):
    def __init__(self, status_code: int):
        super().__init__(f"retryable HTTP {status_code}")
        self.status_code = status_code


def create_async_client(settings: HttpSettings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(settings.timeout_s),
        headers={"User-Agent": settings.user_agent, "Accept": "application/json"},
        limits=httpx.Limits(max_connections=settings.max_concurrency * 2,
                            max_keepalive_connections=settings.max_concurrency),
        follow_redirects=True,
    )


async def get_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict[str, Any],
    settings: HttpSettings,
) -> dict:
    """GET with exponential backoff + jitter; raises ExternalServiceError."""

    async def _once() -> dict:
        resp = await client.get(url, params=params)
        if resp.status_code == 429 or resp.status_code >= 500:
            raise _RetryableStatus(resp.status_code)
        if resp.status_code >= 400:
            raise ExternalServiceError(
                f"GET {url} returned HTTP {resp.status_code}",
                detail={"body": resp.text[:400], "url": str(resp.url)},
            )
        return resp.json()

    runner = retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential_jitter(initial=0.5, max=8.0),
        retry=retry_if_exception_type((_RetryableStatus, httpx.TransportError)),
        reraise=True,
    )(_once)

    try:
        return await runner()
    except _RetryableStatus as exc:
        raise ExternalServiceError(
            f"GET {url} failed after {settings.max_retries} attempts (HTTP {exc.status_code})"
        ) from exc
    except httpx.TransportError as exc:
        raise ExternalServiceError(f"GET {url} transport error: {exc}") from exc
