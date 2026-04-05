from __future__ import annotations

import tempfile
from pathlib import Path
from urllib.parse import urlparse

import httpx
from backend.agents.base import BaseAgent, build_agent_app
from backend.agents.browser_use_events import emit_browser_use_event
from backend.agents.browser_use_marketplaces import (
    BrowserUseListingCheckpointResult,
    build_depop_listing_abort_task,
    build_depop_listing_prepare_task,
    build_depop_listing_revision_task,
    build_depop_listing_submit_task,
)
from backend.agents.browser_use_support import (
    BrowserUseRuntimeUnavailable,
    build_browser_use_metadata,
    classify_browser_use_failure,
    get_browser_profile_path,
    run_structured_browser_task,
)
from backend.schemas import AgentTaskRequest, DepopListingOutput


class DepopListingAgent(BaseAgent):
    ALLOWED_DOMAINS = ["depop.com", "www.depop.com"]
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

        browser_use_result, browser_use_error, profile_available = await self.try_browser_use_listing(
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
            "listing_status": "fallback",
            "ready_for_confirmation": False,
            "draft_status": "fallback",
            "draft_url": None,
            "listing_preview": {
                "title": title,
                "description": description,
                "price": suggested_price,
                "condition": condition,
                "clean_photo_url": vision_analysis.get("clean_photo_url"),
            },
            "execution_mode": "fallback",
            "browser_use_error": browser_use_error,
            "browser_use": self.build_runtime_metadata(
                browser_use_result=browser_use_result,
                browser_use_error=browser_use_error,
                profile_available=profile_available,
            ),
        }
        if browser_use_result is not None:
            output["listing_status"] = browser_use_result.get("listing_status") or "ready_for_confirmation"
            output["ready_for_confirmation"] = bool(browser_use_result.get("ready_for_confirmation", True))
            output["draft_status"] = browser_use_result.get("draft_status") or "ready"
            output["draft_url"] = browser_use_result.get("draft_url")
            output["form_screenshot_url"] = browser_use_result.get("form_screenshot_url")
            output["execution_mode"] = "browser_use"
        elif browser_use_error is not None:
            await emit_browser_use_event(
                session_id=request.session_id,
                pipeline=request.pipeline,
                step=request.step,
                event_type="browser_use_fallback",
                data={
                    "agent_name": self.slug,
                    "platform": "depop",
                    "error": browser_use_error,
                },
            )
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
                "listing_status": output["listing_status"],
                "ready_for_confirmation": output["ready_for_confirmation"],
                "draft_status": output["draft_status"],
                "draft_url": output.get("draft_url"),
                "form_screenshot_url": output.get("form_screenshot_url"),
                "source": output["execution_mode"],
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
    ) -> tuple[dict[str, str | bool | None] | None, str | None, bool]:
        image_path = await self.resolve_image_to_local_path(image_urls)
        task = build_depop_listing_prepare_task(
            title=title,
            description=description,
            suggested_price=suggested_price,
            category_path=category_path,
            image_path=image_path,
        )
        return await self.run_browser_use_listing_checkpoint(task=task)

    async def apply_browser_use_listing_revision(
        self,
        *,
        listing_output: dict[str, object],
        revision_instructions: str,
    ) -> tuple[dict[str, str | bool | None] | None, str | None, bool]:
        task = build_depop_listing_revision_task(
            title=str(listing_output.get("title", "")),
            description=str(listing_output.get("description", "")),
            suggested_price=float(listing_output.get("suggested_price", 0.0)),
            category_path=str(listing_output.get("category_path", "")),
            revision_instructions=revision_instructions,
        )
        return await self.run_browser_use_listing_checkpoint(task=task)

    async def submit_browser_use_listing(self) -> tuple[dict[str, str | bool | None] | None, str | None, bool]:
        return await self.run_browser_use_listing_checkpoint(task=build_depop_listing_submit_task())

    async def abort_browser_use_listing(self) -> tuple[dict[str, str | bool | None] | None, str | None, bool]:
        return await self.run_browser_use_listing_checkpoint(task=build_depop_listing_abort_task())

    async def run_browser_use_listing_checkpoint(
        self,
        *,
        task: str,
    ) -> tuple[dict[str, str | bool | None] | None, str | None, bool]:
        profile_path = Path(get_browser_profile_path("depop"))
        if not profile_path.exists():
            return None, "profile_missing", False
        try:
            return (
                await run_structured_browser_task(
                    task=task,
                    output_model=BrowserUseListingCheckpointResult,
                    operation_name=self._infer_listing_operation(task),
                    allowed_domains=self.ALLOWED_DOMAINS,
                    user_data_dir=str(profile_path),
                    keep_alive=True,
                    max_steps=18,
                    max_failures=3,
                ),
                None,
                True,
            )
        except (BrowserUseRuntimeUnavailable, Exception) as exc:
            return None, classify_browser_use_failure(exc, operation=self._infer_listing_operation(task)), True

    async def resolve_image_to_local_path(self, image_urls: list[str]) -> str | None:
        for candidate in image_urls:
            if candidate.startswith(("http://", "https://")):
                downloaded = await self.download_remote_image(candidate)
                if downloaded is not None:
                    return downloaded
                continue
            path = Path(candidate)
            if path.exists():
                return str(path.resolve())
        return None

    async def download_remote_image(self, image_url: str) -> str | None:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url, timeout=10.0)
                response.raise_for_status()
        except Exception:
            return None

        suffix = Path(urlparse(image_url).path).suffix or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(response.content)
            return temp_file.name

    def _infer_listing_operation(self, task: str) -> str:
        lowered = task.lower()
        if "apply these revision instructions" in lowered:
            return "apply_listing_revision"
        if "verify the listing is fully populated, then perform the final publish or submit action" in lowered:
            return "submit_prepared_listing"
        if "discard, or otherwise abandon the draft" in lowered:
            return "abort_prepared_listing"
        return "prepare_listing_for_review"

    def build_runtime_metadata(
        self,
        *,
        browser_use_result: dict[str, str | bool | None] | None,
        browser_use_error: str | None,
        profile_available: bool,
    ) -> dict[str, object]:
        if browser_use_result is not None:
            return build_browser_use_metadata(
                mode="browser_use",
                attempted_live_run=True,
                profile_name="depop",
                profile_available=True,
                detail="Live Depop listing reached the review checkpoint through Browser Use and is waiting for user confirmation.",
            )
        if browser_use_error == "profile_missing" and not profile_available:
            return build_browser_use_metadata(
                mode="skipped",
                attempted_live_run=False,
                profile_name="depop",
                profile_available=False,
                error_category="profile_missing",
                detail="Skipped live Depop draft creation because the warmed depop profile is missing.",
            )
        return build_browser_use_metadata(
            mode="fallback",
            attempted_live_run=browser_use_error not in {None, "runtime_unavailable"},
            profile_name="depop",
            profile_available=profile_available,
            error_category=browser_use_error,
            detail="Used deterministic fallback listing metadata.",
        )


agent = DepopListingAgent()
app = build_agent_app(agent)


async def revise_sell_listing_for_review(
    *,
    listing_output: dict[str, object],
    revision_instructions: str,
) -> tuple[dict[str, str | bool | None] | None, str | None, bool]:
    return await agent.apply_browser_use_listing_revision(
        listing_output=listing_output,
        revision_instructions=revision_instructions,
    )


async def submit_sell_listing() -> tuple[dict[str, str | bool | None] | None, str | None, bool]:
    return await agent.submit_browser_use_listing()


async def abort_sell_listing() -> tuple[dict[str, str | bool | None] | None, str | None, bool]:
    return await agent.abort_browser_use_listing()
