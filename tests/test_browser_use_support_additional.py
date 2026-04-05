from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from backend.agents import browser_use_support
import backend.agents.depop_listing_agent as depop_listing_module


@pytest.mark.asyncio
async def test_run_structured_browser_task_stops_session_when_agent_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    class DemoOutput(BaseModel):
        title: str

    captured: dict[str, object] = {}

    class FakeAgent:
        def __init__(self, **kwargs: object) -> None:
            captured["agent_kwargs"] = kwargs

        async def run(self) -> object:
            raise RuntimeError("browser tab closed")

    class FakeSession:
        def __init__(self, *, browser_profile: object) -> None:
            captured["browser_profile"] = browser_profile
            self.stopped = False

        async def stop(self) -> None:
            self.stopped = True
            captured["stopped"] = True

    def fake_browser_profile(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(**kwargs)

    def fake_llm(*, model: str, api_key: str) -> SimpleNamespace:
        captured["model"] = model
        captured["api_key"] = api_key
        return SimpleNamespace(model=model, api_key=api_key)

    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.delenv("BROWSER_USE_FORCE_FALLBACK", raising=False)
    monkeypatch.setattr(
        browser_use_support,
        "import_browser_use_dependencies",
        lambda: (FakeAgent, FakeSession, fake_browser_profile, fake_llm),
    )

    with pytest.raises(RuntimeError, match="browser tab closed"):
        await browser_use_support.run_structured_browser_task(
            task="Navigate somewhere",
            output_model=DemoOutput,
            allowed_domains=["example.com"],
            user_data_dir="/tmp/demo",
            keep_alive=True,
        )

    assert captured["model"] == "gemini-2.5-flash"
    assert captured["api_key"] == "test-key"
    assert captured["browser_profile"].allowed_domains == ["example.com"]
    assert captured["browser_profile"].user_data_dir == "/tmp/demo"
    assert captured["browser_profile"].keep_alive is True
    assert captured["stopped"] is True


def test_classify_browser_use_failure_marks_task_execution_errors_as_result_invalid() -> None:
    assert (
        browser_use_support.classify_browser_use_failure(
            browser_use_support.BrowserUseTaskExecutionError("no structured result")
        )
        == "result_invalid"
    )


@pytest.mark.asyncio
async def test_depop_listing_agent_downloads_remote_images_and_falls_back_to_local_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class FakeResponse:
        content = b"remote-image-bytes"

        def raise_for_status(self) -> None:
            return None

    class FakeAsyncClient:
        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

        async def get(self, url: str, timeout: float) -> FakeResponse:
            assert url == "https://images.example.com/remote.jpg"
            assert timeout == 10.0
            return FakeResponse()

    local_image = tmp_path / "image.jpg"
    local_image.write_bytes(b"fake-image-bytes")

    monkeypatch.setattr(depop_listing_module.httpx, "AsyncClient", lambda: FakeAsyncClient())

    remote_path = await depop_listing_module.agent.resolve_image_to_local_path(
        ["https://images.example.com/remote.jpg"]
    )
    assert remote_path is not None
    assert Path(remote_path).read_bytes() == b"remote-image-bytes"
    assert remote_path.endswith(".jpg")

    async def broken_download_remote_image(image_url: str) -> str | None:
        assert image_url == "https://images.example.com/remote-fails.jpg"
        return None

    monkeypatch.setattr(depop_listing_module.agent, "download_remote_image", broken_download_remote_image)

    fallback_path = await depop_listing_module.agent.resolve_image_to_local_path(
        [
            "https://images.example.com/remote-fails.jpg",
            str(local_image),
        ]
    )

    assert fallback_path == str(local_image.resolve())
