from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.agents.base import BaseAgent, build_agent_app
from backend.agents.trend_analysis import compute_trend, compute_velocity
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
        low_sold_price = sold_comps["low_sold_price"]
        high_sold_price = sold_comps["high_sold_price"]

        condition_multiplier = self.CONDITION_LISTING_MULTIPLIERS.get(condition, 1.0)
        recommended_list_price = self.compute_recommended_list_price(
            median_sold_price=median_sold_price,
            low_sold_price=low_sold_price,
            high_sold_price=high_sold_price,
            condition_multiplier=condition_multiplier,
            sample_size=sample_size,
        )

        sourcing_cost = max(6.0, round(median_sold_price * 0.38, 2))
        marketplace_fees = round(recommended_list_price * 0.13, 2)
        expected_profit = round(recommended_list_price - sourcing_cost - marketplace_fees, 2)

        spread_ratio = self.compute_spread_ratio(
            median_sold_price=median_sold_price,
            low_sold_price=low_sold_price,
            high_sold_price=high_sold_price,
        )
        base_confidence = 0.58
        sample_bonus = min(sample_size, 16) * 0.015
        known_brand_bonus = 0.08 if brand != "Unknown" else 0.0
        known_item_bonus = 0.05 if detected_item != "item" else 0.0
        strong_condition_bonus = 0.04 if condition in {"new", "excellent", "great"} else 0.0
        spread_penalty = min(0.03, spread_ratio * 0.008)
        pricing_confidence = round(
            min(
                0.96,
                base_confidence + sample_bonus + known_brand_bonus + known_item_bonus + strong_condition_bonus - spread_penalty,
            ),
            2,
        )

        # Synthesize comp list from summary stats for trend + velocity analysis
        synthetic_comps = self._synthesize_comps(sold_comps)
        trend = compute_trend(synthetic_comps)
        velocity = compute_velocity(synthetic_comps)

        descriptor = f"{brand} {detected_item}".strip() if brand != "Unknown" else detected_item

        return {
            "agent": self.slug,
            "display_name": self.display_name,
            "summary": f"Priced {descriptor} at ${recommended_list_price} with estimated profit ${expected_profit}",
            "recommended_list_price": recommended_list_price,
            "expected_profit": expected_profit,
            "pricing_confidence": pricing_confidence,
            "median_sold_price": median_sold_price,
            "trend": trend,
            "velocity": velocity,
        }

    @staticmethod
    def compute_recommended_list_price(
        *,
        median_sold_price: float,
        low_sold_price: float,
        high_sold_price: float,
        condition_multiplier: float,
        sample_size: int,
    ) -> float:
        baseline = median_sold_price * condition_multiplier
        comp_floor = max(low_sold_price * 1.04, median_sold_price * 0.9)
        comp_ceiling = high_sold_price * 1.02
        clamped_price = min(max(baseline, comp_floor), comp_ceiling)
        if sample_size < 6:
            clamped_price = (clamped_price * 0.6) + (median_sold_price * 0.4)
        return round(clamped_price, 2)

    @staticmethod
    def compute_spread_ratio(*, median_sold_price: float, low_sold_price: float, high_sold_price: float) -> float:
        anchor = max(median_sold_price, 1.0)
        return max(0.0, (high_sold_price - low_sold_price) / anchor)

    @staticmethod
    def _synthesize_comps(sold_comps: dict) -> list[dict]:
        """Build a synthetic comp list from summary stats for trend/velocity.

        Since EbaySoldCompsAgent returns median/low/high/sample_size rather
        than individual sales, we synthesize a plausible list spread across
        the last 90 days to give compute_trend and compute_velocity enough data.
        """
        now = datetime.now(timezone.utc)
        median_price = sold_comps.get("median_sold_price", 40.0)
        low_price = sold_comps.get("low_sold_price", median_price * 0.7)
        high_price = sold_comps.get("high_sold_price", median_price * 1.3)
        sample_size = max(sold_comps.get("sample_size", 8), 4)

        comps = []
        for i in range(sample_size):
            # Spread sales across 0–90 days ago
            days_ago = int((i / max(sample_size - 1, 1)) * 85)
            date = (now - timedelta(days=days_ago)).date().isoformat()

            # Simulate slight price increase over time (recent items cost more)
            progress = i / max(sample_size - 1, 1)
            price = round(low_price + (high_price - low_price) * (1 - progress * 0.4), 2)

            comps.append({"price": price, "date_sold": date})

        return comps


agent = PricingAgent()
app = build_agent_app(agent)
