from __future__ import annotations

import asyncio
import threading
import time

from fastapi.testclient import TestClient

from backend.schemas import PipelineStartRequest, SessionEvent
from backend.session import session_manager


SELL_PAYLOAD = {
    "user_id": "demo-user-1",
    "input": {
        "image_urls": ["https://example.com/shirt.jpg"],
        "notes": "Vintage Nike tee",
    },
    "metadata": {"source": "test"},
}


def wait_for_terminal_result(client: TestClient, session_id: str, timeout: float = 3.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/result/{session_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.02)
    raise AssertionError(f"Session {session_id} did not reach a terminal state")


def test_healthcheck(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "agent_execution_mode": "local_functions",
        "agent_count": "10",
        "fetch_enabled": False,
        "agentverse_credentials_present": False,
    }


def test_healthcheck_includes_cors_headers_for_browser_clients(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "https://example.com"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] in {"*", "https://example.com"}


def test_sell_start_preflight_returns_cors_headers(client: TestClient) -> None:
    response = client.options(
        "/sell/start",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://example.com"
    assert "POST" in response.headers["access-control-allow-methods"]


def test_healthcheck_get_includes_cors_header_for_browser_origin(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "https://diamondhacks.app"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"


def test_healthcheck_options_supports_cors_preflight(client: TestClient) -> None:
    response = client.options(
        "/health",
        headers={
            "Origin": "https://diamondhacks.app",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://diamondhacks.app"
    assert "GET" in response.headers["access-control-allow-methods"]


def test_sell_start_creates_session_and_result_url(client: TestClient) -> None:
    response = client.post("/sell/start", json=SELL_PAYLOAD)

    assert response.status_code == 200
    payload = response.json()
    assert payload["pipeline"] == "sell"
    assert payload["status"] == "queued"
    assert payload["session_id"]
    assert payload["stream_url"].endswith(f"/stream/{payload['session_id']}")
    assert payload["result_url"].endswith(f"/result/{payload['session_id']}")

    session = wait_for_terminal_result(client, payload["session_id"])
    assert session["pipeline"] == "sell"
    assert session["status"] == "completed"


def test_buy_start_creates_session(client: TestClient) -> None:
    response = client.post(
        "/buy/start",
        json={
            "user_id": "demo-user-2",
            "input": {"query": "Nike vintage tee size M", "budget": 45},
            "metadata": {"source": "test"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pipeline"] == "buy"
    assert payload["status"] == "queued"

    session = wait_for_terminal_result(client, payload["session_id"])
    assert session["pipeline"] == "buy"
    assert session["status"] == "completed"


def test_result_unknown_session_returns_404(client: TestClient) -> None:
    response = client.get("/result/not-a-real-session")

    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found"}


def test_stream_unknown_session_returns_404(client: TestClient) -> None:
    response = client.get("/stream/not-a-real-session")

    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found"}


def test_stream_emits_keepalive_ping_during_idle_gap(client: TestClient, monkeypatch) -> None:
    session_id = "keepalive-session"
    asyncio.run(
        session_manager.create_session(
            session_id=session_id,
            pipeline="sell",
            request=PipelineStartRequest(
                user_id="keepalive-user",
                input={"image_urls": ["https://example.com/item.jpg"]},
            ),
        )
    )
    monkeypatch.setattr("backend.main.KEEPALIVE_INTERVAL", 0.01, raising=False)

    def emit_terminal_event() -> None:
        time.sleep(0.03)
        asyncio.run(
            session_manager.append_event(
                SessionEvent(
                    session_id=session_id,
                    event_type="pipeline_complete",
                    pipeline="sell",
                    data={"outputs": {}},
                )
            )
        )

    worker = threading.Thread(target=emit_terminal_event, daemon=True)
    worker.start()

    with client.stream("GET", f"/stream/{session_id}") as response:
        assert response.status_code == 200
        chunks: list[str] = []
        for chunk in response.iter_text():
            chunks.append(chunk)
            if "event: pipeline_complete" in "".join(chunks):
                break

    worker.join(timeout=1)
    body = "".join(chunks)
    assert ": ping" in body
    assert "event: pipeline_complete" in body
