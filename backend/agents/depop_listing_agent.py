from __future__ import annotations

from pathlib import Path

from backend.agents.base import BaseAgent, build_agent_app
from backend.agents.browser_use_events import emit_browser_use_event
from backend.agents.browser_use_marketplaces import BrowserUseListingDraftResult, build_depop_listing_task
from backend.agents.browser_use_support import (
    BrowserUseRuntimeUnavailable,
    get_browser_profile_path,
    run_structured_browser_task,
)
from backend.schemas import AgentTaskRequest, DepopListingOutput


class DepopListingAgent(BaseAgent):
    CATEGORY_PATHS = {
        "hoodie": "Men/Tops/Hoodies",
        "jacket": "Men/Outerwear/Jackets",
        "tee": "Men/Tops/T-Shirts",
        "t-shirt": "Men/Tops/T-Shirts",
        "sweater": "Men/Tops/Sweaters",
        "shirt": "Men/Tops/Shirts",
        "pants": "Men/Bottoms/Pants",
        "jeans": "Men/Bottoms/Jeans",
        "shorts": "Men/Bottoms/Shorts",
        "dress": "Women/Dresses",
        "skirt": "Women/Bottoms/Skirts",
        "bag": "Accessories/Bags",
        "hat": "Accessories/Hats",
        "shoes": "Shoes",
        "sneakers": "Shoes/Sneakers",
    }

    def __init__(self) -> None:
        super().__init__(
            slug="depop_listing_agent",
            display_name="Depop Listing Agent",
            output_model=DepopListingOutput,
        )

    async def build_output(self, request: AgentTaskRequest) -> dict:
        original_input = request.input["original_input"]
        previous_outputs = request.input["previous_outputs"]

        vision_analysis = previous_outputs["vision_analysis"]
        sold_comps = previous_outputs["ebay_sold_comps"]
        pricing = previous_outputs["pricing"]

        brand = vision_analysis["brand"]
        detected_item = vision_analysis["detected_item"]
        condition = vision_analysis["condition"]
        notes = (original_input.get("notes") or "").strip()

        descriptor = f"{brand} {detected_item}".strip() if brand != "Unknown" else detected_item.title()
        title = f"{descriptor} - {condition.title()} Condition"
        category_path = self.CATEGORY_PATHS.get(detected_item.lower(), "Men/Tops/T-Shirts")
        suggested_price = pricing["recommended_list_price"]

        note_sentence = notes if notes else f"Clean {detected_item} ready to list."
        description = (
            f"{descriptor} in {condition} condition. {note_sentence} "
            f"Suggested list price: ${suggested_price}. "
            f"Recent eBay sold range: ${sold_comps['low_sold_price']}-${sold_comps['high_sold_price']} "
            f"across {sold_comps['sample_size']} comps. "
            f"Estimated profit: ${pricing['expected_profit']}."
        )

        browser_use_result = await self.try_browser_use_listing(
            title=title,
            description=description,
            suggested_price=suggested_price,
            category_path=category_path,
            image_urls=original_input.get("image_urls") or [],
        )

        output = {
            "agent": self.slug,
            "display_name": self.display_name,
            "summary": f"Prepared Depop listing for {descriptor} at ${suggested_price}",
            "title": title,
            "description": description,
            "suggested_price": suggested_price,
            "category_path": category_path,
            "draft_status": "fallback",
            "listing_preview": {
                "title": title,
                "description": description,
                "price": suggested_price,
            },
        }
        if browser_use_result is not None:
            output["draft_status"] = browser_use_result["draft_status"]
            output["form_screenshot_url"] = browser_use_result.get("form_screenshot_url")
        await emit_browser_use_event(
            session_id=request.session_id,
            pipeline=request.pipeline,
            step=request.step,
            event_type="draft_created",
            data={
                "agent_name": self.slug,
                "platform": "depop",
                "title": title,
                "suggested_price": suggested_price,
                "category_path": category_path,
                "draft_status": output["draft_status"],
                "form_screenshot_url": output.get("form_screenshot_url"),
                "source": "browser_use" if browser_use_result is not None else "fallback",
            },
        )
        return output

    async def try_browser_use_listing(
        self,
        *,
        title: str,
        description: str,
        suggested_price: float,
        category_path: str,
        image_urls: list[str],
    ) -> dict[str, str | None] | None:
        profile_path = Path(get_browser_profile_path("depop"))
        if not profile_path.exists():
            return None
        image_path = self.get_local_image_path(image_urls)
        task = build_depop_listing_task(
            title=title,
            description=description,
            suggested_price=suggested_price,
            category_path=category_path,
            image_path=image_path,
        )
        try:
            return await run_structured_browser_task(
                task=task,
                output_model=BrowserUseListingDraftResult,
                allowed_domains=["depop.com", "www.depop.com"],
                user_data_dir=str(profile_path),
                keep_alive=True,
                max_steps=18,
                max_failures=3,
            )
        except (BrowserUseRuntimeUnavailable, Exception):
            return None

    def get_local_image_path(self, image_urls: list[str]) -> str | None:
        for candidate in image_urls:
            if candidate.startswith(("http://", "https://")):
                continue
            path = Path(candidate)
            if path.exists():
                return str(path.resolve())
        return None


agent = DepopListingAgent()
app = build_agent_app(agent)
