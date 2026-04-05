from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

import backend.browser_use_runtime_audit as browser_use_runtime_audit
from backend.agents import browser_use_support
from backend.main import app
from backend.session import session_manager


@pytest.fixture(autouse=True)
def clean_sessions(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv("AGENTVERSE_API_KEY", raising=False)
    asyncio.run(session_manager.reset())
    yield
    asyncio.run(session_manager.reset())


@pytest.fixture(autouse=True)
def guard_browser_use_imports(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_browser_use_imports() -> None:
        raise RuntimeError("Browser Use imports disabled during pytest to avoid local AppKit crashes")

    monkeypatch.setenv("PYTEST_DISABLE_BROWSER_USE_IMPORTS", "true")
    monkeypatch.setattr(browser_use_support, "import_browser_use_dependencies", fail_browser_use_imports)
    monkeypatch.setattr(browser_use_runtime_audit, "import_browser_use_dependencies", fail_browser_use_imports)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
