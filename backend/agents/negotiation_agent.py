from __future__ import annotations

from pathlib import Path

from backend.agents.base import BaseAgent, build_agent_app
from backend.agents.browser_use_events import emit_browser_use_event
from backend.agents.browser_use_marketplaces import BrowserUseNegotiationResult, build_negotiation_task
from backend.agents.browser_use_support import BrowserUseRuntimeUnavailable, get_browser_profile_path, run_structured_browser_task
from backend.schemas import AgentTaskRequest, NegotiationOutput


class NegotiationAgent(BaseAgent):
    PLATFORM_DISCOUNTS = {
        "offerup": 0.9,
        "mercari": 0.92,
        "ebay": 0.91,
        "depop": 0.93,
    }

    def __init__(self) -> None:
        super().__init__(
            slug="negotiation_agent",
            display_name="Negotiation Agent",
            output_model=NegotiationOutput,
        )

    async def build_output(self, request: AgentTaskRequest) -> dict:
        previous_outputs = request.input["previous_outputs"]
        top_choice = previous_outputs["ranking"]["top_choice"]
        median_price = float(previous_outputs["ranking"]["median_price"])
        search_outputs = previous_outputs

        all_candidates = [
            listing
            for step in ("depop_search", "ebay_search", "mercari_search", "offerup_search")
            for listing in search_outputs[step]["results"]
        ]
        all_candidates.sort(key=lambda item: (item["price"], item["title"]))

        prioritized_titles = {top_choice["title"]}
        matched_top_choice = next((listing for listing in all_candidates if listing["title"] == top_choice["title"]), None)
        prioritized_candidates = [
            matched_top_choice
            or {
                "platform": top_choice["platform"],
                "title": top_choice["title"],
                "price": top_choice["price"],
                "condition": "good",
                "seller": top_choice["seller"],
                "url": top_choice["url"],
                "seller_score": top_choice.get("seller_score", 0),
                "posted_at": top_choice["posted_at"],
            }
        ]
        for listing in all_candidates:
            if listing["title"] in prioritized_titles:
                continue
            prioritized_candidates.append(listing)
            prioritized_titles.add(listing["title"])
            if len(prioritized_candidates) == 3:
                break

        offers = []
        for listing in prioritized_candidates:
            prepared_offer = self.build_prepared_offer(listing=listing, median_price=median_price)
            await emit_browser_use_event(
                session_id=request.session_id,
                pipeline=request.pipeline,
                step=request.step,
                event_type="offer_prepared",
                data={
                    "agent_name": self.slug,
                    "platform": prepared_offer["platform"],
                    "seller": prepared_offer["seller"],
                    "listing_url": prepared_offer["listing_url"],
                    "listing_title": prepared_offer["listing_title"],
                    "target_price": prepared_offer["target_price"],
                    "source": "deterministic",
                },
            )
            live_result = await self.try_send_offer(prepared_offer)
            if live_result is not None:
                prepared_offer.update(live_result)
                await emit_browser_use_event(
                    session_id=request.session_id,
                    pipeline=request.pipeline,
                    step=request.step,
                    event_type="offer_sent" if prepared_offer["status"] == "sent" else "offer_failed",
                    data={
                        "agent_name": self.slug,
                        "platform": prepared_offer["platform"],
                        "seller": prepared_offer["seller"],
                        "listing_url": prepared_offer["listing_url"],
                        "listing_title": prepared_offer["listing_title"],
                        "target_price": prepared_offer["target_price"],
                        "status": prepared_offer["status"],
                        "conversation_url": prepared_offer["conversation_url"],
                        "failure_reason": prepared_offer["failure_reason"],
                        "source": "browser_use",
                    },
                )
            offers.append(prepared_offer)

        processed_statuses = {offer["status"] for offer in offers}
        if processed_statuses == {"prepared"}:
            summary = (
                f"Prepared {len(offers)} negotiation attempts starting with "
                f"{top_choice['seller']} on {top_choice['platform']}"
            )
        else:
            summary = (
                f"Processed {len(offers)} negotiation attempts starting with "
                f"{top_choice['seller']} on {top_choice['platform']}"
            )

        return {
            "agent": self.slug,
            "display_name": self.display_name,
            "summary": summary,
            "offers": offers,
        }

    def build_prepared_offer(self, *, listing: dict[str, object], median_price: float) -> dict[str, object]:
        platform = str(listing["platform"])
        target_price = round(
            max(median_price, float(listing["price"]) * self.PLATFORM_DISCOUNTS.get(platform, 0.92)),
            2,
        )
        return {
            "platform": platform,
            "seller": listing["seller"],
            "listing_url": listing["url"],
            "listing_title": listing["title"],
            "target_price": target_price,
            "message": (
                f"Hi! I love this listing. Would you consider ${target_price} "
                f"for {listing['title']}? I can pay right away."
            ),
            "status": "prepared",
            "failure_reason": None,
            "conversation_url": None,
        }

    async def try_send_offer(self, prepared_offer: dict[str, object]) -> dict[str, object] | None:
        platform = str(prepared_offer["platform"])
        profile_path = Path(get_browser_profile_path(platform))
        if not profile_path.exists():
            return None

        task = build_negotiation_task(
            platform=platform,
            listing_url=str(prepared_offer["listing_url"]),
            message=str(prepared_offer["message"]),
            target_price=float(prepared_offer["target_price"]),
        )
        try:
            return await run_structured_browser_task(
                task=task,
                output_model=BrowserUseNegotiationResult,
                allowed_domains=self.allowed_domains_for_platform(platform),
                user_data_dir=str(profile_path),
                keep_alive=True,
                max_steps=16,
                max_failures=3,
            )
        except BrowserUseRuntimeUnavailable:
            return None
        except Exception as exc:
            return {
                "status": "failed",
                "failure_reason": str(exc),
                "conversation_url": None,
            }

    def allowed_domains_for_platform(self, platform: str) -> list[str]:
        return {
            "depop": ["depop.com", "www.depop.com"],
            "ebay": ["ebay.com", "www.ebay.com"],
            "mercari": ["mercari.com", "www.mercari.com"],
            "offerup": ["offerup.com", "www.offerup.com"],
        }[platform]


agent = NegotiationAgent()
app = build_agent_app(agent)
