from __future__ import annotations

import base64
import json
import mimetypes
import re
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import httpx

from backend.agents.base import AgentPaused, BaseAgent, build_agent_app
from backend.config import (
    get_clean_photo_provider,
    get_gemini_api_key,
    get_gemini_image_model,
    get_gemini_model,
    get_image_processing_timeout_seconds,
    get_nano_banana_api_key,
    get_nano_banana_api_url,
    get_vision_low_confidence_threshold,
)
from backend.schemas import AgentTaskRequest, SellPipelineInput, VisionAnalysisOutput


class VisionAgent(BaseAgent):
    CLEAN_PHOTO_PROMPT = (
        "Edit this product photo into a clean resale listing shot. "
        "Keep the item identical and centered. Remove the background and replace it with a pure white studio background. "
        "Do not add props, text, logos, watermarks, hands, or extra objects. Preserve realistic shape, color, and details."
    )
    PROMPT = """Identify this resale item from the photo and return JSON only:
{
  "brand": "Nike",
  "item_name": "Air Jordan 1 Retro High OG",
  "model": "Air Jordan 1",
  "category": "footwear",
  "condition": "good",
  "condition_notes": "slight creasing on toe box",
  "confidence": 0.92,
  "color": "red black white",
  "size_visible": "10.5",
  "search_query": "Nike Air Jordan 1 Retro High OG Chicago"
}

Rules:
- condition must be exactly one of: excellent, good, fair
- confidence must be a float from 0.0 to 1.0
- search_query must be optimized for eBay sold listing search
- if the brand is unknown, return "Unknown"
- return JSON only with no markdown or preamble"""

    BRAND_KEYWORDS = {
        "nike": "Nike",
        "adidas": "Adidas",
        "levis": "Levi's",
        "levi": "Levi's",
        "carhartt": "Carhartt",
        "patagonia": "Patagonia",
        "supreme": "Supreme",
        "stussy": "Stussy",
        "ralphlauren": "Ralph Lauren",
        "polo": "Polo Ralph Lauren",
        "sony": "Sony",
        "apple": "Apple",
        "northface": "The North Face",
    }
    CATEGORY_KEYWORDS = {
        "hoodie": ("apparel", "hoodie"),
        "sweatshirt": ("apparel", "sweatshirt"),
        "crewneck": ("apparel", "sweatshirt"),
        "jacket": ("outerwear", "jacket"),
        "coat": ("outerwear", "coat"),
        "jeans": ("bottoms", "jeans"),
        "denim": ("bottoms", "jeans"),
        "pants": ("bottoms", "pants"),
        "shirt": ("apparel", "shirt"),
        "tee": ("apparel", "t-shirt"),
        "tshirt": ("apparel", "t-shirt"),
        "sneakers": ("footwear", "sneakers"),
        "sneaker": ("footwear", "sneakers"),
        "shoes": ("footwear", "shoes"),
        "shoe": ("footwear", "shoes"),
        "boots": ("footwear", "boots"),
        "bag": ("accessories", "bag"),
        "hat": ("accessories", "hat"),
        "cap": ("accessories", "hat"),
        "headphones": ("accessories", "headphones"),
        "airpods": ("accessories", "headphones"),
        "camera": ("accessories", "camera"),
    }
    CATEGORY_HINT_DEFAULTS = {
        "apparel": "shirt",
        "outerwear": "jacket",
        "bottoms": "pants",
        "footwear": "shoes",
        "accessories": "bag",
        "electronics": "accessories",
    }
    CONDITION_KEYWORDS = {
        "new": "new",
        "newwithtags": "new",
        "nwt": "new",
        "mint": "excellent",
        "excellent": "excellent",
        "great": "great",
        "good": "good",
        "fair": "fair",
        "worn": "fair",
        "distressed": "fair",
    }

    def __init__(self) -> None:
        super().__init__(
            slug="vision_agent",
            display_name="Vision Agent",
            output_model=VisionAnalysisOutput,
        )

    async def build_output(self, request: AgentTaskRequest) -> dict:
        original_input = SellPipelineInput.model_validate(request.input.get("original_input", {}))
        image_payload = await self._resolve_image_payload(original_input)
        identification = await self.identify_item(original_input, image_payload)

        if self._should_pause_for_confirmation(identification):
            item_label = identification.get("item_name") or identification.get("detected_item") or "item"
            brand = identification.get("brand") or "Unknown"
            message = f"Not sure. Is this a {brand} {item_label}?".strip()
            raise AgentPaused(
                message,
                output={
                    "suggestion": self._strip_private_fields(identification),
                    "message": message,
                },
            )

        if image_payload is not None and not identification.get("clean_photo_url"):
            clean_photo_url = await self.generate_clean_photo(image_payload)
            if clean_photo_url:
                identification["clean_photo_url"] = clean_photo_url

        return self._finalize_output(identification)

    async def build_output_from_correction(
        self,
        original_input: dict[str, Any] | SellPipelineInput,
        corrected_item: dict[str, Any],
        *,
        suggestion: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sell_input = (
            original_input if isinstance(original_input, SellPipelineInput) else SellPipelineInput.model_validate(original_input)
        )
        merged: dict[str, Any] = {}
        if suggestion:
            merged.update(suggestion)
        merged.update(corrected_item)

        identification = self._normalize_identification(merged, sell_input, source="manual")
        identification["confidence"] = max(
            self._coerce_confidence(merged.get("confidence")) or 1.0,
            get_vision_low_confidence_threshold(),
        )

        image_payload = await self._resolve_image_payload(sell_input)
        if image_payload is not None and not identification.get("clean_photo_url"):
            clean_photo_url = await self.generate_clean_photo(image_payload)
            if clean_photo_url:
                identification["clean_photo_url"] = clean_photo_url

        return self._finalize_output(identification)

    async def identify_item(
        self,
        original_input: SellPipelineInput,
        image_payload: dict[str, str] | None,
    ) -> dict[str, Any]:
        if image_payload is not None and get_gemini_api_key():
            try:
                gemini_result = await self._identify_with_gemini(image_payload)
                return self._normalize_identification(gemini_result, original_input, source="gemini")
            except Exception:
                pass

        return self._fallback_identification(original_input)

    async def generate_clean_photo(self, image_payload: dict[str, str]) -> str | None:
        provider = get_clean_photo_provider()

        if provider in {"auto", "gemini"} and get_gemini_api_key().strip():
            try:
                return await self._generate_clean_photo_with_gemini(image_payload)
            except Exception:
                if provider == "gemini":
                    return None

        api_url = get_nano_banana_api_url().strip()
        api_key = get_nano_banana_api_key().strip()
        if provider == "gemini" or not api_url or not api_key:
            return None

        async with httpx.AsyncClient(timeout=get_image_processing_timeout_seconds()) as client:
            response = await client.post(
                api_url,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "image": image_payload["data"],
                    "mime_type": image_payload["mime_type"],
                },
            )
            response.raise_for_status()
            payload = response.json()

        return self._extract_clean_photo_url(payload)

    async def _generate_clean_photo_with_gemini(self, image_payload: dict[str, str]) -> str | None:
        model = get_gemini_image_model().strip()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        request_body = {
            "contents": [
                {
                    "parts": [
                        {"text": self.CLEAN_PHOTO_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": image_payload["mime_type"],
                                "data": image_payload["data"],
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["IMAGE", "TEXT"],
            },
        }

        async with httpx.AsyncClient(timeout=max(60.0, get_image_processing_timeout_seconds())) as client:
            response = await client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": get_gemini_api_key(),
                },
                json=request_body,
            )
            response.raise_for_status()
            payload = response.json()

        generated = self._extract_generated_image(payload)
        if generated is None:
            return None

        mime_type, data = generated
        extension = mimetypes.guess_extension(mime_type) or ".png"
        with tempfile.NamedTemporaryFile(prefix="diamondhacks_clean_photo_", suffix=extension, delete=False) as handle:
            handle.write(base64.b64decode(data))
            return handle.name

    async def _identify_with_gemini(self, image_payload: dict[str, str]) -> dict[str, Any]:
        model = get_gemini_model().strip()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        request_body = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": image_payload["mime_type"],
                                "data": image_payload["data"],
                            }
                        },
                        {"text": self.PROMPT},
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=get_image_processing_timeout_seconds()) as client:
            response = await client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": get_gemini_api_key(),
                },
                json=request_body,
            )
            response.raise_for_status()
            payload = response.json()

        raw_text = self._extract_gemini_text(payload)
        return json.loads(self._clean_json_block(raw_text))

    async def _resolve_image_payload(self, original_input: SellPipelineInput) -> dict[str, str] | None:
        if original_input.image_base64:
            mime_type, data = self._normalize_inline_image(original_input.image_base64, original_input.image_mime_type)
            return {"mime_type": mime_type, "data": data}

        should_fetch_remote = bool(
            get_gemini_api_key().strip() or (get_nano_banana_api_key().strip() and get_nano_banana_api_url().strip())
        )
        for candidate in original_input.image_urls:
            if candidate.startswith(("http://", "https://")):
                if not should_fetch_remote:
                    continue
                try:
                    return await self._fetch_remote_image(candidate)
                except Exception:
                    continue
            path = Path(candidate)
            if path.exists() and path.is_file():
                return self._read_local_image(path)

        return None

    async def _fetch_remote_image(self, url: str) -> dict[str, str]:
        async with httpx.AsyncClient(timeout=get_image_processing_timeout_seconds(), follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            mime_type = response.headers.get("content-type", "").split(";")[0].strip() or self._guess_mime_type(url)
            return {
                "mime_type": mime_type or "image/jpeg",
                "data": base64.b64encode(response.content).decode("utf-8"),
            }

    def _read_local_image(self, path: Path) -> dict[str, str]:
        mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        return {
            "mime_type": mime_type,
            "data": base64.b64encode(path.read_bytes()).decode("utf-8"),
        }

    def _normalize_inline_image(self, image_base64: str, image_mime_type: str | None) -> tuple[str, str]:
        data_url_match = re.match(r"^data:(?P<mime>[\w.+-]+/[\w.+-]+);base64,(?P<data>.+)$", image_base64, re.DOTALL)
        if data_url_match:
            mime_type = data_url_match.group("mime")
            data = data_url_match.group("data")
        else:
            mime_type = image_mime_type or "image/jpeg"
            data = image_base64

        normalized = re.sub(r"\s+", "", data)
        base64.b64decode(normalized, validate=True)
        return mime_type, normalized

    def _extract_generated_image(self, payload: dict[str, Any]) -> tuple[str, str] | None:
        candidates = payload.get("candidates") or []
        for candidate in candidates:
            content = candidate.get("content") or {}
            parts = content.get("parts") or []
            for part in parts:
                if not isinstance(part, dict):
                    continue
                inline_data = part.get("inline_data") or part.get("inlineData")
                if not isinstance(inline_data, dict):
                    continue
                mime_type = inline_data.get("mime_type") or inline_data.get("mimeType")
                data = inline_data.get("data")
                if isinstance(mime_type, str) and isinstance(data, str) and data:
                    return mime_type, data
        return None

    def _extract_gemini_text(self, payload: dict[str, Any]) -> str:
        candidates = payload.get("candidates") or []
        for candidate in candidates:
            content = candidate.get("content") or {}
            parts = content.get("parts") or []
            text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
            if text.strip():
                return text.strip()
        raise ValueError("Gemini response did not contain text output")

    def _normalize_identification(
        self,
        raw_result: dict[str, Any],
        original_input: SellPipelineInput,
        *,
        source: str,
    ) -> dict[str, Any]:
        fallback = self._fallback_identification(original_input)
        brand = self._clean_text(raw_result.get("brand")) or fallback["brand"]
        item_name = (
            self._clean_text(raw_result.get("item_name"))
            or self._clean_text(raw_result.get("item"))
            or self._clean_text(raw_result.get("detected_item"))
            or fallback["item_name"]
        )
        model = self._clean_text(raw_result.get("model"))
        search_query = self._clean_text(raw_result.get("search_query"))
        condition = self._normalize_condition(raw_result.get("condition")) or fallback["condition"]
        condition_notes = self._clean_text(raw_result.get("condition_notes"))
        color = self._clean_text(raw_result.get("color"))
        size_visible = self._clean_text(raw_result.get("size_visible"))
        confidence = self._coerce_confidence(raw_result.get("confidence"))

        category_hint = self._clean_text(raw_result.get("category"))
        explicit_detected_item = self._clean_text(raw_result.get("detected_item"))
        if explicit_detected_item:
            category, detected_item = self._infer_category_and_item(
                " ".join(part for part in (explicit_detected_item, category_hint or "") if part),
                category_hint=category_hint,
            )
            if detected_item == "item":
                detected_item = explicit_detected_item.lower()
            if category == "unknown" and category_hint:
                category = category_hint.lower()
        else:
            category, detected_item = self._infer_category_and_item(
                " ".join(part for part in (item_name, model, search_query, category_hint, original_input.notes or "") if part),
                category_hint=category_hint,
            )

        return {
            "brand": brand,
            "detected_item": detected_item,
            "category": category,
            "condition": condition,
            "item_name": item_name,
            "model": model,
            "condition_notes": condition_notes,
            "confidence": confidence if confidence is not None else fallback["confidence"],
            "color": color,
            "size_visible": size_visible,
            "search_query": search_query or fallback["search_query"],
            "clean_photo_url": self._clean_text(raw_result.get("clean_photo_url")),
            "analysis_source": source,
        }

    def _fallback_identification(self, original_input: SellPipelineInput) -> dict[str, Any]:
        normalized_text = self._combined_text(original_input)
        tokens = normalized_text.split()

        brand = self._detect_brand(tokens)
        category, detected_item = self._detect_category(tokens)
        condition = self._detect_condition(tokens)
        item_name = f"{brand} {detected_item}".strip() if brand != "Unknown" else detected_item.title()
        search_query = item_name if item_name and item_name.lower() != "item" else "used resale item"

        return {
            "brand": brand,
            "detected_item": detected_item,
            "category": category,
            "condition": condition,
            "item_name": item_name,
            "model": None,
            "condition_notes": None,
            "confidence": 0.86 if detected_item != "item" or brand != "Unknown" else 0.71,
            "color": None,
            "size_visible": None,
            "search_query": search_query,
            "clean_photo_url": None,
            "analysis_source": "fallback",
        }

    def _finalize_output(self, identification: dict[str, Any]) -> dict[str, Any]:
        item_label = identification.get("item_name") or identification.get("detected_item") or "item"
        condition = identification.get("condition") or "good"
        summary = f"Identified {item_label} in {condition} condition"

        return {
            "agent": self.slug,
            "display_name": self.display_name,
            "summary": summary,
            **self._strip_private_fields(identification),
        }

    def _strip_private_fields(self, identification: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in identification.items() if key != "analysis_source"}

    def _should_pause_for_confirmation(self, identification: dict[str, Any]) -> bool:
        if identification.get("analysis_source") != "gemini":
            return False
        confidence = self._coerce_confidence(identification.get("confidence"))
        if confidence is None:
            return False
        return confidence < get_vision_low_confidence_threshold()

    def _combined_text(self, original_input: SellPipelineInput) -> str:
        notes = original_input.notes or ""
        parts = [notes]
        parts.extend(self._url_to_tokens(url) for url in original_input.image_urls if isinstance(url, str))
        normalized = " ".join(parts).lower()
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        return " ".join(normalized.split())

    def _url_to_tokens(self, url: str) -> str:
        parsed = urlparse(url)
        return unquote(f"{parsed.netloc} {parsed.path}")

    def _detect_brand(self, tokens: list[str]) -> str:
        for token in tokens:
            compact = token.replace("'", "")
            if compact in self.BRAND_KEYWORDS:
                return self.BRAND_KEYWORDS[compact]
        return "Unknown"

    def _detect_category(self, tokens: list[str]) -> tuple[str, str]:
        for token in tokens:
            if token in self.CATEGORY_KEYWORDS:
                return self.CATEGORY_KEYWORDS[token]
        return "unknown", "item"

    def _detect_condition(self, tokens: list[str]) -> str:
        for token in tokens:
            if token in self.CONDITION_KEYWORDS:
                return self.CONDITION_KEYWORDS[token]
        return "good"

    def _infer_category_and_item(self, text: str, *, category_hint: str | None = None) -> tuple[str, str]:
        normalized = re.sub(r"[^a-z0-9]+", " ", text.lower())
        tokens = normalized.split()
        category, detected_item = self._detect_category(tokens)
        if category != "unknown":
            return category, detected_item
        if category_hint:
            hint = category_hint.lower().strip()
            if hint in self.CATEGORY_HINT_DEFAULTS:
                return hint, self.CATEGORY_HINT_DEFAULTS[hint]
        return "unknown", "item"

    def _normalize_condition(self, condition: Any) -> str | None:
        if not isinstance(condition, str):
            return None
        normalized = re.sub(r"[^a-z]+", "", condition.lower())
        return self.CONDITION_KEYWORDS.get(normalized)

    def _coerce_confidence(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return None

    def _clean_text(self, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        cleaned = value.strip()
        return cleaned or None

    def _guess_mime_type(self, value: str) -> str:
        return mimetypes.guess_type(value)[0] or "image/jpeg"

    def _clean_json_block(self, text: str) -> str:
        stripped = text.strip()
        stripped = stripped.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return stripped

    def _extract_clean_photo_url(self, payload: Any) -> str | None:
        if isinstance(payload, dict):
            for key in ("url", "image_url", "output_url", "clean_photo_url"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            for value in payload.values():
                extracted = self._extract_clean_photo_url(value)
                if extracted:
                    return extracted
        if isinstance(payload, list):
            for item in payload:
                extracted = self._extract_clean_photo_url(item)
                if extracted:
                    return extracted
        return None


async def build_corrected_vision_output(
    original_input: dict[str, Any],
    corrected_item: dict[str, Any],
    *,
    suggestion: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return await agent.build_output_from_correction(original_input, corrected_item, suggestion=suggestion)


agent = VisionAgent()
app = build_agent_app(agent)
