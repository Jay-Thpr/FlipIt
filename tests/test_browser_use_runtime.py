from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from backend.agents import browser_use_support


def test_browser_use_runtime_ready_requires_key_and_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setattr(browser_use_support, "import_browser_use_dependencies", lambda: (_ for _ in ()).throw(AssertionError))
    assert browser_use_support.browser_use_runtime_ready() is False

    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setattr(browser_use_support, "import_browser_use_dependencies", lambda: (object(), object(), object(), object()))
    assert browser_use_support.browser_use_runtime_ready() is True


def test_browser_use_runtime_ready_respects_forced_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("BROWSER_USE_FORCE_FALLBACK", "true")
    monkeypatch.setattr(browser_use_support, "import_browser_use_dependencies", lambda: (object(), object(), object(), object()))
    assert browser_use_support.browser_use_runtime_ready() is False


def test_get_browser_profile_path_uses_configured_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BROWSER_USE_PROFILE_ROOT", "tmp-browser-profiles")
    assert browser_use_support.get_browser_profile_path("depop").endswith("/tmp-browser-profiles/depop")


def test_browser_profile_kwargs_include_stealth_and_optional_fields() -> None:
    kwargs = browser_use_support.get_browser_profile_kwargs(
        allowed_domains=["depop.com"],
        user_data_dir="/tmp/depop",
        keep_alive=True,
    )
    assert kwargs == {
        "headless": False,
        "stealth": True,
        "allowed_domains": ["depop.com"],
        "user_data_dir": "/tmp/depop",
        "keep_alive": True,
    }


@pytest.mark.asyncio
async def test_run_structured_browser_task_returns_validated_output(monkeypatch: pytest.MonkeyPatch) -> None:
    class DemoOutput(BaseModel):
        title: str
        count: int

    captured: dict[str, object] = {}

    class FakeHistory:
        def final_result(self, output_model: type[BaseModel]) -> BaseModel:
            return output_model(title="browser ok", count=3)

    class FakeAgent:
        def __init__(self, **kwargs: object) -> None:
            captured["agent_kwargs"] = kwargs

        async def run(self) -> FakeHistory:
            return FakeHistory()

    class FakeSession:
        def __init__(self, *, browser_profile: object) -> None:
            captured["browser_profile"] = browser_profile
            self.stopped = False

        async def stop(self) -> None:
            self.stopped = True
            captured["stopped"] = True

    def fake_browser_profile(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(**kwargs)

    def fake_llm(*, model: str) -> SimpleNamespace:
        captured["model"] = model
        return SimpleNamespace(model=model)

    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.delenv("BROWSER_USE_FORCE_FALLBACK", raising=False)
    monkeypatch.setattr(
        browser_use_support,
        "import_browser_use_dependencies",
        lambda: (FakeAgent, FakeSession, fake_browser_profile, fake_llm),
    )

    result = await browser_use_support.run_structured_browser_task(
        task="Navigate somewhere",
        output_model=DemoOutput,
        allowed_domains=["example.com"],
        user_data_dir="/tmp/demo",
        keep_alive=True,
        max_steps=7,
    )

    assert result == {"title": "browser ok", "count": 3}
    assert captured["model"] == "gemini-2.0-flash"
    assert captured["browser_profile"].allowed_domains == ["example.com"]
    assert captured["browser_profile"].user_data_dir == "/tmp/demo"
    assert captured["browser_profile"].keep_alive is True
    assert captured["agent_kwargs"]["max_steps"] == 7
    assert captured["stopped"] is True


@pytest.mark.asyncio
async def test_run_structured_browser_task_fails_cleanly_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    class DemoOutput(BaseModel):
        title: str

    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(browser_use_support.BrowserUseRuntimeUnavailable):
        await browser_use_support.run_structured_browser_task(
            task="Navigate somewhere",
            output_model=DemoOutput,
        )


def test_browser_task_timeout_respects_prd_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_TIMEOUT_SECONDS", "12")
    assert browser_use_support.get_browser_task_timeout_seconds() == 30.0

    monkeypatch.setenv("AGENT_TIMEOUT_SECONDS", "45")
    assert browser_use_support.get_browser_task_timeout_seconds() == 45.0


def test_summarize_browser_use_error_handles_empty_and_runtime_errors() -> None:
    assert browser_use_support.summarize_browser_use_error(RuntimeError("dom changed")) == "dom changed"
    assert (
        browser_use_support.summarize_browser_use_error(
            browser_use_support.BrowserUseRuntimeUnavailable("missing key")
        )
        == "missing key"
    )


def test_classify_browser_use_failure_returns_stable_categories() -> None:
    assert browser_use_support.classify_browser_use_failure(
        browser_use_support.BrowserUseRuntimeUnavailable("missing key")
    ) == "runtime_unavailable"
    assert browser_use_support.classify_browser_use_failure(RuntimeError("profile login expired")) == "profile_missing"
    assert browser_use_support.classify_browser_use_failure(RuntimeError("page navigation timeout")) == "browser_error"
    assert browser_use_support.classify_browser_use_failure(RuntimeError("sold page changed")) == "browser_error"


def test_build_browser_use_metadata_returns_expected_shape() -> None:
    assert browser_use_support.build_browser_use_metadata(
        mode="fallback",
        attempted_live_run=True,
        profile_name="depop",
        profile_available=True,
        error_category="navigation",
        detail="DOM changed",
    ) == {
        "mode": "fallback",
        "attempted_live_run": True,
        "profile_name": "depop",
        "profile_available": True,
        "error_category": "navigation",
        "detail": "DOM changed",
    }
