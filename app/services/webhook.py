from __future__ import annotations

import asyncio
import logging
from concurrent.futures import Future
from typing import Any

import httpx

logger = logging.getLogger(__name__)


DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BACKOFF_BASE_SECONDS = 1.0
DEFAULT_TIMEOUT_SECONDS = 10.0


async def deliver_webhook(
    url: str,
    payload: dict[str, Any],
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    backoff_base_seconds: float = DEFAULT_BACKOFF_BASE_SECONDS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    client: httpx.AsyncClient | None = None,
) -> None:
    """Dispara um webhook com retry/backoff exponencial simples."""

    own_client = client is None
    client = client or httpx.AsyncClient(timeout=timeout_seconds)

    try:
        last_exc: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt >= max_attempts:
                    break
                await asyncio.sleep(backoff_base_seconds * (2 ** (attempt - 1)))

        logger.warning("Webhook delivery failed after %s attempts: %s", max_attempts, last_exc)
    finally:
        if own_client:
            await client.aclose()


def send_webhook_background(
    url: str,
    payload: dict[str, Any],
    *,
    loop: asyncio.AbstractEventLoop | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    backoff_base_seconds: float = DEFAULT_BACKOFF_BASE_SECONDS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    client: httpx.AsyncClient | None = None,
) -> Future | None:
    """Agenda entrega assíncrona usando o loop existente ou executa inline."""

    if not url:
        return

    coro = deliver_webhook(
        url,
        payload,
        max_attempts=max_attempts,
        backoff_base_seconds=backoff_base_seconds,
        timeout_seconds=timeout_seconds,
        client=client,
    )

    if loop:
        if loop.is_running():
            return asyncio.run_coroutine_threadsafe(coro, loop)
        return loop.run_until_complete(coro)

    asyncio.run(coro)
    return None
