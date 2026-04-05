"""AI-powered item analysis and professional image generation using Gemini."""
from __future__ import annotations

import base64
import io
import json
import logging
import os
from typing import Any

import httpx
import google.generativeai as genai
from PIL import Image

logger = logging.getLogger(__name__)

_NANO_BANANA_API_KEY: str | None = None


def _get_api_key() -> str:
    """Return the Gemini API key from NANO_BANANA_API_KEY env var."""
    global _NANO_BANANA_API_KEY
    if _NANO_BANANA_API_KEY is None:
        _NANO_BANANA_API_KEY = os.getenv("NANO_BANANA_API_KEY", "")
    if not _NANO_BANANA_API_KEY:
        raise RuntimeError("NANO_BANANA_API_KEY is not configured")
    return _NANO_BANANA_API_KEY


def _configure_genai() -> None:
    """Configure the google-generativeai SDK with the Nano Banana API key."""
    genai.configure(api_key=_get_api_key())


async def _download_image(photo_url: str) -> bytes:
    """Download an image from a URL and return the raw bytes."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(photo_url)
        resp.raise_for_status()
        return resp.content


async def analyze_item_photo(photo_url: str) -> dict[str, str]:
    """Use Gemini Vision to analyze a product photo.

    Returns:
        {"name": str, "description": str, "condition": str}
    """
    _configure_genai()

    image_bytes = await _download_image(photo_url)
    image = Image.open(io.BytesIO(image_bytes))

    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = (
        "You are a resale marketplace expert. Analyze this product photo and return "
        "a JSON object with exactly these fields:\n"
        '- "name": a concise product name suitable for a marketplace listing title\n'
        '- "description": a detailed resale listing description (2-4 sentences) that '
        "highlights key features, brand, materials, and selling points. Write it in a "
        "style that would appeal to buyers on platforms like Depop, eBay, or Mercari.\n"
        '- "condition": one of "New", "Like New", "Very Good", "Good", "Fair", "Poor"\n\n'
        "Return ONLY valid JSON, no markdown fences or extra text."
    )

    response = model.generate_content([prompt, image])
    text = response.text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Gemini returned non-JSON for analysis, using fallback parse: %s", text[:200])
        result = {
            "name": "Unknown Item",
            "description": text[:500] if text else "No description available.",
            "condition": "Good",
        }

    return {
        "name": result.get("name", "Unknown Item"),
        "description": result.get("description", "No description available."),
        "condition": result.get("condition", "Good"),
    }


async def generate_professional_photos(
    photo_url: str,
    item_name: str,
    count: int = 4,
) -> list[str]:
    """Use Gemini image generation to create professional product photos.

    Returns a list of base64-encoded image data strings.
    """
    _configure_genai()

    image_bytes = await _download_image(photo_url)
    source_image = Image.open(io.BytesIO(image_bytes))

    model = genai.GenerativeModel("gemini-2.0-flash")

    generated_images: list[str] = []

    angle_prompts = [
        "front-facing hero shot on a clean white background, professional studio lighting",
        "slight angle view on a neutral light gray background, soft shadow, lifestyle feel",
        "close-up detail shot highlighting texture and quality, clean background",
        "styled flat-lay arrangement on a minimal white surface, overhead perspective",
        "three-quarter angle with soft gradient background, commercial product photography",
        "side profile view on seamless white, editorial product photography style",
    ]

    for i in range(count):
        angle = angle_prompts[i % len(angle_prompts)]
        prompt = (
            f"Generate a professional e-commerce product photo of this {item_name}. "
            f"Style: {angle}. "
            "The photo should look like it belongs on a premium resale marketplace. "
            "High resolution, sharp focus, professionally lit. "
            "Make it look appealing to online shoppers."
        )

        try:
            response = model.generate_content(
                [prompt, source_image],
                generation_config=genai.GenerationConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )

            # Extract image data from the response
            image_data = _extract_image_from_response(response)
            if image_data:
                generated_images.append(image_data)
            else:
                logger.warning("No image data in Gemini response for photo %d", i)
        except Exception:
            logger.exception("Failed to generate professional photo %d for %s", i, item_name)
            # Continue with remaining photos rather than failing entirely

    return generated_images


def _extract_image_from_response(response: Any) -> str | None:
    """Extract base64 image data from a Gemini response containing an image.

    Returns the base64-encoded string, or None if no image found.
    """
    try:
        if not response.candidates:
            return None

        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                # inline_data has mime_type and data (bytes)
                raw_bytes = part.inline_data.data
                if isinstance(raw_bytes, bytes):
                    return base64.b64encode(raw_bytes).decode("utf-8")
                # Already base64 string
                if isinstance(raw_bytes, str):
                    return raw_bytes
    except (AttributeError, IndexError, TypeError):
        logger.exception("Failed to extract image from Gemini response")

    return None
