from __future__ import annotations

import time

from fastapi.testclient import TestClient


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
    }


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
