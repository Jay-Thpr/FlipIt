from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.session import session_manager


@pytest.fixture(autouse=True)
def clean_sessions(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv("AGENTVERSE_API_KEY", raising=False)
    asyncio.run(session_manager.reset())
    yield
    asyncio.run(session_manager.reset())


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
