from __future__ import annotations

from typing import Any

from backend.agents.base import BaseAgent, build_agent_app
from backend.agents.browser_use_events import emit_browser_use_event
from backend.agents.browser_use_support import (
    BrowserUseRuntimeUnavailable,
    build_browser_use_metadata,
    classify_browser_use_failure,
    run_structured_browser_task,
)
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
        item_name = vision_analysis.get("item_name") or detected_item
        descriptor = item_name if brand == "Unknown" or item_name.lower().startswith(brand.lower()) else f"{brand} {item_name}"

        browser_use_result, browser_use_error = await self.try_browser_use_research(
            brand=brand,
            detected_item=detected_item,
            condition=condition,
            search_query=vision_analysis.get("search_query"),
        )
        if browser_use_result is not None:
            sample_size = int(browser_use_result["sample_size"])
            return {
                "agent": self.slug,
                "display_name": self.display_name,
                "summary": f"Extracted {sample_size} sold eBay comps for {descriptor} with Browser Use",
                "median_sold_price": browser_use_result["median_sold_price"],
                "low_sold_price": browser_use_result["low_sold_price"],
                "high_sold_price": browser_use_result["high_sold_price"],
                "sample_size": sample_size,
                "execution_mode": "browser_use",
                "browser_use_error": None,
                "browser_use": build_browser_use_metadata(
                    mode="browser_use",
                    attempted_live_run=True,
                    detail=f"Live Browser Use sold comps returned {sample_size} comparable sales.",
                ),
            }

        base_price = self.CATEGORY_BASE_PRICES.get(detected_item, self.CATEGORY_BASE_PRICES["item"])
        brand_multiplier = self.BRAND_MULTIPLIERS.get(brand, 1.0)
        condition_multiplier = self.CONDITION_MULTIPLIERS.get(condition, 1.0)
        median_price = round(base_price * brand_multiplier * condition_multiplier, 2)

        spread_ratio = 0.22 if condition in {"new", "excellent"} else 0.3
        low_price = round(max(8.0, median_price * (1 - spread_ratio)), 2)
        high_price = round(median_price * (1 + spread_ratio), 2)
        sample_size = self.CONDITION_SAMPLE_SIZES.get(condition, 12)

        if browser_use_error is not None:
            await emit_browser_use_event(
                session_id=request.session_id,
                pipeline=request.pipeline,
                step=request.step,
                event_type="browser_use_fallback",
                data={
                    "agent_name": self.slug,
                    "platform": "ebay",
                    "error": browser_use_error,
                },
            )

        return {
            "agent": self.slug,
            "display_name": self.display_name,
            "summary": f"Estimated {sample_size} sold eBay comps for {descriptor}",
            "median_sold_price": median_price,
            "low_sold_price": low_price,
            "high_sold_price": high_price,
            "sample_size": sample_size,
            "execution_mode": "fallback",
            "browser_use_error": browser_use_error,
            "browser_use": build_browser_use_metadata(
                mode="fallback",
                attempted_live_run=browser_use_error not in {None, "runtime_unavailable"},
                error_category=browser_use_error,
                detail="Used deterministic sold comps estimator.",
            ),
        }

    async def try_browser_use_research(
        self,
        *,
        brand: str,
        detected_item: str,
        condition: str,
        search_query: str | None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        from pydantic import BaseModel

        query_text = search_query or " ".join(part for part in (brand, detected_item) if part and part != "Unknown") or detected_item
        query = "+".join(query_text.split())
        condition_code = {
            "new": "1000",
            "excellent": "1500",
            "great": "3000",
            "good": "3000",
            "fair": "7000",
        }.get(condition, "3000")
        url = (
            "https://www.ebay.com/sch/i.html"
            f"?_nkw={query}"
            "&LH_Sold=1"
            "&LH_Complete=1"
            f"&LH_ItemCondition={condition_code}"
            "&_sop=13"
            "&_ipg=24"
        )

        class SoldCompResearch(BaseModel):
            median_sold_price: float
            low_sold_price: float
            high_sold_price: float
            sample_size: int

        task = f"""
Navigate to: {url}
Wait for sold listing cards to load.
From the first 10 sold listings that show a visible final sold price, calculate:
- median_sold_price
- low_sold_price
- high_sold_price
- sample_size
Return only JSON matching the schema.
"""

        try:
            return (
                await run_structured_browser_task(
                    task=task,
                    output_model=SoldCompResearch,
                    allowed_domains=["ebay.com", "www.ebay.com"],
                    max_steps=12,
                    max_failures=3,
                ),
                None,
            )
        except (BrowserUseRuntimeUnavailable, Exception) as exc:
            return None, classify_browser_use_failure(exc)


agent = EbaySoldCompsAgent()
app = build_agent_app(agent)
