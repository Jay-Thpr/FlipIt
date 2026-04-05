from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from backend.item_store import item_store
from backend.main import app
from backend.session import session_manager


@pytest.fixture(autouse=True)
def clean_sessions() -> Iterator[None]:
    asyncio.run(session_manager.reset())
    item_store.reset()
    yield
    asyncio.run(session_manager.reset())
    item_store.reset()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
