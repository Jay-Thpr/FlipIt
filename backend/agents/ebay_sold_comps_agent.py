from __future__ import annotations

from backend.agents.base import BaseAgent, build_agent_app
from backend.schemas import AgentTaskRequest, EbaySoldCompsOutput


class EbaySoldCompsAgent(BaseAgent):
    CATEGORY_BASE_PRICES = {
        "hoodie": 48.0,
        "sweatshirt": 42.0,
        "jacket": 72.0,
        "coat": 88.0,
        "jeans": 46.0,
        "pants": 39.0,
        "shirt": 28.0,
        "t-shirt": 24.0,
        "sneakers": 64.0,
        "shoes": 52.0,
        "boots": 74.0,
        "bag": 44.0,
        "hat": 26.0,
        "item": 32.0,
    }

    BRAND_MULTIPLIERS = {
        "Nike": 1.15,
        "Adidas": 1.08,
        "Levi's": 1.05,
        "Carhartt": 1.22,
        "Patagonia": 1.28,
        "Supreme": 1.35,
        "Stussy": 1.18,
        "Ralph Lauren": 1.12,
        "Polo Ralph Lauren": 1.14,
        "Unknown": 1.0,
    }

    CONDITION_MULTIPLIERS = {
        "new": 1.3,
        "excellent": 1.15,
        "great": 1.08,
        "good": 1.0,
        "fair": 0.82,
    }

    CONDITION_SAMPLE_SIZES = {
        "new": 8,
        "excellent": 11,
        "great": 13,
        "good": 16,
        "fair": 10,
    }

    def __init__(self) -> None:
        super().__init__(
            slug="ebay_sold_comps_agent",
            display_name="eBay Sold Comps Agent",
            output_model=EbaySoldCompsOutput,
        )

    async def build_output(self, request: AgentTaskRequest) -> dict:
        vision_analysis = request.input["previous_outputs"]["vision_analysis"]
        detected_item = vision_analysis["detected_item"]
        brand = vision_analysis["brand"]
        condition = vision_analysis["condition"]

        base_price = self.CATEGORY_BASE_PRICES.get(detected_item, self.CATEGORY_BASE_PRICES["item"])
        brand_multiplier = self.BRAND_MULTIPLIERS.get(brand, 1.0)
        condition_multiplier = self.CONDITION_MULTIPLIERS.get(condition, 1.0)
        median_price = round(base_price * brand_multiplier * condition_multiplier, 2)

        spread_ratio = 0.22 if condition in {"new", "excellent"} else 0.3
        low_price = round(max(8.0, median_price * (1 - spread_ratio)), 2)
        high_price = round(median_price * (1 + spread_ratio), 2)
        sample_size = self.CONDITION_SAMPLE_SIZES.get(condition, 12)

        descriptor = f"{brand} {detected_item}".strip() if brand != "Unknown" else detected_item

        return {
            "agent": self.slug,
            "display_name": self.display_name,
            "summary": f"Estimated {sample_size} sold eBay comps for {descriptor}",
            "median_sold_price": median_price,
            "low_sold_price": low_price,
            "high_sold_price": high_price,
            "sample_size": sample_size,
        }


agent = EbaySoldCompsAgent()
app = build_agent_app(agent)
