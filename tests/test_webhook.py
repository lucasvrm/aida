import asyncio
import json

import httpx
import pytest

from app.services.webhook import deliver_webhook, send_webhook_background


@pytest.mark.anyio
async def test_deliver_webhook_success():
    received: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        received.append(json.loads(request.content))
        return httpx.Response(200)

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)

    await deliver_webhook("https://example.com/webhook", {"ok": True}, client=client)
    await client.aclose()

    assert received == [{"ok": True}]


@pytest.mark.anyio
async def test_deliver_webhook_retries(monkeypatch):
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        status = 500 if attempts < 3 else 200
        return httpx.Response(status)

    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)

    await deliver_webhook(
        "https://example.com/webhook",
        {"ok": True},
        client=client,
        max_attempts=3,
        backoff_base_seconds=0.1,
    )
    await client.aclose()

    assert attempts == 3
    assert sleep_calls == [0.1, 0.2]


def test_send_webhook_background_uses_loop():
    received: list[str] = []

    loop = asyncio.new_event_loop()

    def handler(request: httpx.Request) -> httpx.Response:
        received.append(request.url.host)
        return httpx.Response(200)

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)

    try:
        send_webhook_background(
            "https://example.com/webhook",
            {"ok": True},
            loop=loop,
            max_attempts=1,
            backoff_base_seconds=0,
            timeout_seconds=1,
            client=client,
        )
        loop.run_until_complete(asyncio.sleep(0))
        assert received == ["example.com"]
    finally:
        loop.run_until_complete(client.aclose())
        loop.close()
