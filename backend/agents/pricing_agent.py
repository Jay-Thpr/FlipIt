from __future__ import annotations

from backend.agents.base import BaseAgent, build_agent_app
from backend.schemas import AgentTaskRequest, PricingOutput


class PricingAgent(BaseAgent):
    CONDITION_LISTING_MULTIPLIERS = {
        "new": 1.18,
        "excellent": 1.11,
        "great": 1.06,
        "good": 1.0,
        "fair": 0.93,
    }

    def __init__(self) -> None:
        super().__init__(
            slug="pricing_agent",
            display_name="Pricing Agent",
            output_model=PricingOutput,
        )

    async def build_output(self, request: AgentTaskRequest) -> dict:
        previous_outputs = request.input["previous_outputs"]
        vision_analysis = previous_outputs["vision_analysis"]
        sold_comps = previous_outputs["ebay_sold_comps"]

        median_sold_price = sold_comps["median_sold_price"]
        condition = vision_analysis["condition"]
        brand = vision_analysis["brand"]
        detected_item = vision_analysis["detected_item"]
        sample_size = sold_comps["sample_size"]

        condition_multiplier = self.CONDITION_LISTING_MULTIPLIERS.get(condition, 1.0)
        recommended_list_price = round(median_sold_price * condition_multiplier, 2)

        sourcing_cost = max(6.0, round(median_sold_price * 0.38, 2))
        marketplace_fees = round(recommended_list_price * 0.13, 2)
        expected_profit = round(recommended_list_price - sourcing_cost - marketplace_fees, 2)

        base_confidence = 0.58
        sample_bonus = min(sample_size, 16) * 0.015
        known_brand_bonus = 0.08 if brand != "Unknown" else 0.0
        known_item_bonus = 0.05 if detected_item != "item" else 0.0
        strong_condition_bonus = 0.04 if condition in {"new", "excellent", "great"} else 0.0
        pricing_confidence = round(
            min(0.96, base_confidence + sample_bonus + known_brand_bonus + known_item_bonus + strong_condition_bonus),
            2,
        )

        descriptor = f"{brand} {detected_item}".strip() if brand != "Unknown" else detected_item

        return {
            "agent": self.slug,
            "display_name": self.display_name,
            "summary": f"Priced {descriptor} at ${recommended_list_price} with estimated profit ${expected_profit}",
            "recommended_list_price": recommended_list_price,
            "expected_profit": expected_profit,
            "pricing_confidence": pricing_confidence,
        }


agent = PricingAgent()
app = build_agent_app(agent)
