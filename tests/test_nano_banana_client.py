from __future__ import annotations

import pytest

from backend.nano_banana.client import NanoBananaClient, NanoBananaSettings


def test_settings_from_env_reads_nano_banana_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NANO_BANANA_API_URL", "http://127.0.0.1:8010/clean")
    monkeypatch.setenv("NANO_BANANA_API_KEY", "test-key")
    monkeypatch.setenv("IMAGE_PROCESSING_TIMEOUT_SECONDS", "12")

    settings = NanoBananaSettings.from_env()

    assert settings.api_url == "http://127.0.0.1:8010/clean"
    assert settings.api_key == "test-key"
    assert settings.timeout_seconds == 12.0
    assert settings.is_configured() is True


def test_extract_clean_photo_url_handles_nested_payloads() -> None:
    payload = {
        "data": {
            "images": [
                {"preview_url": "ignore-me"},
                {"output": {"clean_photo_url": "https://cdn.example.com/clean-photo.jpg"}},
            ]
        }
    }

    assert NanoBananaClient.extract_clean_photo_url(payload) == "https://cdn.example.com/clean-photo.jpg"


@pytest.mark.asyncio
async def test_generate_clean_photo_posts_expected_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"clean_photo_url": "mock-nano-result"}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            calls.append({"timeout": kwargs.get("timeout")})

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):
            calls.append({"url": url, "headers": headers, "json": json})
            return FakeResponse()

    monkeypatch.setattr("backend.nano_banana.client.httpx.AsyncClient", FakeAsyncClient)

    client = NanoBananaClient(
        NanoBananaSettings(
            api_url="http://127.0.0.1:8010/clean",
            api_key="test-nano-key",
            timeout_seconds=9.0,
        )
    )

    result = await client.generate_clean_photo({"mime_type": "image/jpeg", "data": "ZmFrZQ=="})

    assert result is not None
    assert result.clean_photo_url == "mock-nano-result"
    assert calls == [
        {"timeout": 9.0},
        {
            "url": "http://127.0.0.1:8010/clean",
            "headers": {"Authorization": "Bearer test-nano-key"},
            "json": {"image": "ZmFrZQ==", "mime_type": "image/jpeg"},
        },
    ]
