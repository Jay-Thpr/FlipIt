from __future__ import annotations

import re
from urllib.parse import urlparse, unquote

from backend.agents.base import BaseAgent, build_agent_app
from backend.schemas import AgentTaskRequest, VisionAnalysisOutput


class VisionAgent(BaseAgent):
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
        "shoes": ("footwear", "shoes"),
        "boots": ("footwear", "boots"),
        "bag": ("accessories", "bag"),
        "hat": ("accessories", "hat"),
        "cap": ("accessories", "hat"),
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
        original_input = request.input.get("original_input", {})
        image_urls = original_input.get("image_urls") or []
        normalized_text = self._combined_text(request)
        tokens = normalized_text.split()

        brand = self._detect_brand(tokens)
        category, detected_item = self._detect_category(tokens)
        condition = self._detect_condition(tokens)
        summary_subject = detected_item if brand == "Unknown" else f"{brand} {detected_item}"
        search_query = self._build_search_query(brand=brand, detected_item=detected_item)
        # Heuristic confidence until Gemini: known brand + non-generic item → higher score.
        if brand != "Unknown" and detected_item not in ("item", "unknown"):
            confidence = 0.88
        elif brand != "Unknown":
            confidence = 0.78
        else:
            confidence = 0.55

        return {
            "agent": self.slug,
            "display_name": self.display_name,
            "summary": f"Inferred {summary_subject.strip()} in {condition} condition",
            "detected_item": detected_item,
            "brand": brand,
            "category": category,
            "condition": condition,
            "confidence": confidence,
            "model": None,
            "clean_photo_url": self._select_clean_photo_url(image_urls),
            "search_query": search_query,
        }

    def _combined_text(self, request: AgentTaskRequest) -> str:
        original_input = request.input.get("original_input", {})
        notes = original_input.get("notes") or ""
        image_urls = original_input.get("image_urls") or []
        parts = [notes]
        parts.extend(self._url_to_tokens(url) for url in image_urls if isinstance(url, str))
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

    def _build_search_query(self, *, brand: str, detected_item: str) -> str | None:
        if brand == "Unknown" and detected_item == "item":
            return None
        if brand == "Unknown":
            return detected_item
        return f"{brand} {detected_item}"

    def _select_clean_photo_url(self, image_urls: list[str]) -> str | None:
        for image_url in image_urls:
            if isinstance(image_url, str) and image_url.strip():
                return image_url.strip()
        return None


agent = VisionAgent()
app = build_agent_app(agent)
