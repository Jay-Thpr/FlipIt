from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class NanoBananaSettings:
    api_url: str
    api_key: str
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "NanoBananaSettings":
        timeout = float(os.getenv("IMAGE_PROCESSING_TIMEOUT_SECONDS", "30"))
        return cls(
            api_url=os.getenv("NANO_BANANA_API_URL", "").strip(),
            api_key=os.getenv("NANO_BANANA_API_KEY", "").strip(),
            timeout_seconds=timeout,
        )

    def is_configured(self) -> bool:
        return bool(self.api_url and self.api_key)


@dataclass(frozen=True)
class NanoBananaResult:
    clean_photo_url: str
    raw_payload: Any


class NanoBananaClient:
    def __init__(self, settings: NanoBananaSettings) -> None:
        self.settings = settings

    @classmethod
    def from_env(cls) -> "NanoBananaClient":
        return cls(NanoBananaSettings.from_env())

    def is_configured(self) -> bool:
        return self.settings.is_configured()

    async def generate_clean_photo(self, image_payload: dict[str, str]) -> NanoBananaResult | None:
        if not self.is_configured():
            return None

        request_payload = self.build_request_payload(image_payload)

        async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
            response = await client.post(
                self.settings.api_url,
                headers={"Authorization": f"Bearer {self.settings.api_key}"},
                json=request_payload,
            )
            response.raise_for_status()
            payload = response.json()

        clean_photo_url = self.extract_clean_photo_url(payload)
        if not clean_photo_url:
            return None
        return NanoBananaResult(clean_photo_url=clean_photo_url, raw_payload=payload)

    @staticmethod
    def build_request_payload(image_payload: dict[str, str]) -> dict[str, str]:
        return {
            "image": image_payload["data"],
            "mime_type": image_payload.get("mime_type", "image/jpeg"),
        }

    @classmethod
    def extract_clean_photo_url(cls, payload: Any) -> str | None:
        if isinstance(payload, str):
            normalized = payload.strip()
            if normalized.startswith(("http://", "https://", "/")):
                return normalized
            return None

        if isinstance(payload, dict):
            for key in ("clean_photo_url", "output_url", "image_url", "url"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value
            for value in payload.values():
                extracted = cls.extract_clean_photo_url(value)
                if extracted:
                    return extracted
            return None

        if isinstance(payload, list):
            for item in payload:
                extracted = cls.extract_clean_photo_url(item)
                if extracted:
                    return extracted
            return None

        return None
