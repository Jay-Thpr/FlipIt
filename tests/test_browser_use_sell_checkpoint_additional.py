from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from backend.agents import browser_use_support
import backend.agents.depop_listing_agent as depop_listing_module


@pytest.mark.asyncio
async def test_run_structured_browser_task_stops_session_when_final_result_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DemoOutput(BaseModel):
        title: str

    captured: dict[str, object] = {}

    class FakeHistory:
        def final_result(self) -> None:
            return None

    class FakeAgent:
        def __init__(self, **kwargs: object) -> None:
            captured["agent_kwargs"] = kwargs

        async def run(self) -> FakeHistory:
            return FakeHistory()

    class FakeSession:
        def __init__(self, *, browser_profile: object) -> None:
            captured["browser_profile"] = browser_profile

        async def stop(self) -> None:
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

    with pytest.raises(
        browser_use_support.BrowserUseTaskExecutionError,
        match="Browser Use returned no structured result for prepare_listing_for_review",
    ):
        await browser_use_support.run_structured_browser_task(
            task="Prepare a listing",
            output_model=DemoOutput,
            operation_name="prepare_listing_for_review",
            allowed_domains=["depop.com"],
            user_data_dir="/tmp/depop",
            keep_alive=True,
        )

    assert captured["browser_profile"].keep_alive is True
    assert captured["api_key"] == "test-key"
    assert captured["stopped"] is True


@pytest.mark.asyncio
async def test_depop_listing_checkpoint_paths_pass_expected_operation_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: list[dict[str, Any]] = []

    async def fake_run_structured_browser_task(**kwargs: Any) -> dict[str, Any]:
        captured.append(kwargs)
        return {
            "listing_status": "ready_for_confirmation",
            "ready_for_confirmation": True,
            "draft_status": "ready",
            "draft_url": None,
            "form_screenshot_url": "artifact://checkpoint",
        }

    profile_root = tmp_path / "profiles"
    depop_profile = profile_root / "depop"
    depop_profile.mkdir(parents=True)

    monkeypatch.setattr(depop_listing_module, "run_structured_browser_task", fake_run_structured_browser_task)
    monkeypatch.setenv("BROWSER_USE_PROFILE_ROOT", str(profile_root))

    async def fake_resolve_image_to_local_path(image_urls: list[str]) -> str | None:
        assert image_urls == ["https://images.example.com/item.jpg"]
        return "/tmp/upload.jpg"

    monkeypatch.setattr(depop_listing_module.agent, "resolve_image_to_local_path", fake_resolve_image_to_local_path)

    await depop_listing_module.agent.try_browser_use_listing(
        title="Patagonia hoodie - Excellent Condition",
        description="Prepared description",
        suggested_price=78.43,
        category_path="Men/Tops/Hoodies",
        image_urls=["https://images.example.com/item.jpg"],
    )
    await depop_listing_module.agent.apply_browser_use_listing_revision(
        listing_output={
            "title": "Patagonia hoodie - Excellent Condition",
            "description": "Prepared description",
            "suggested_price": 78.43,
            "category_path": "Men/Tops/Hoodies",
        },
        revision_instructions="Lower the price to $72",
    )
    await depop_listing_module.agent.submit_browser_use_listing()
    await depop_listing_module.agent.abort_browser_use_listing()

    assert [item["operation_name"] for item in captured] == [
        "prepare_listing_for_review",
        "apply_listing_revision",
        "submit_prepared_listing",
        "abort_prepared_listing",
    ]
    assert all(item["allowed_domains"] == ["depop.com", "www.depop.com"] for item in captured)
    assert all(item["keep_alive"] is True for item in captured)
    assert all(str(item["user_data_dir"]).endswith("/profiles/depop") for item in captured)
    assert "desktop or non-mobile listing layout" in captured[0]["task"]
    assert "Apply these revision instructions" in captured[1]["task"]
    assert "perform the final publish or submit action" in captured[2]["task"]
    assert "Close, discard, or otherwise abandon the draft" in captured[3]["task"]
