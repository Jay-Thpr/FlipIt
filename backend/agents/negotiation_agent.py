from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.agents.base import BaseAgent, build_agent_app
from backend.agents.browser_use_events import emit_browser_use_event
from backend.agents.browser_use_marketplaces import BrowserUseNegotiationResult, build_negotiation_task
from backend.agents.browser_use_support import (
    BrowserUseRuntimeUnavailable,
    build_browser_use_metadata,
    classify_browser_use_failure,
    get_browser_profile_path,
    run_structured_browser_task,
    summarize_browser_use_error,
)
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
        ranking_output = previous_outputs["ranking"]
        top_choice = ranking_output.get("top_choice")
        median_price = float(ranking_output["median_price"])
        budget = request.input["original_input"].get("budget")
        search_outputs = previous_outputs

        if not top_choice or int(ranking_output.get("candidate_count", 0)) == 0:
            return {
                "agent": self.slug,
                "display_name": self.display_name,
                "summary": "No ranked marketplace listings were available for negotiation",
                "offers": [],
                "browser_use": build_browser_use_metadata(
                    mode="skipped",
                    attempted_live_run=False,
                    detail="Skipped negotiation because ranking returned no marketplace candidates.",
                ),
            }

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
        for index, listing in enumerate(prioritized_candidates):
            prepared_offer = self.build_prepared_offer(
                listing=listing,
                median_price=median_price,
                budget=budget,
                is_top_choice=index == 0,
            )
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
                    "source": prepared_offer["execution_mode"],
                },
            )
            live_result = await self.try_send_offer(prepared_offer)
            prepared_offer.update(live_result)
            if prepared_offer["execution_mode"] == "browser_use":
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
                        "source": prepared_offer["execution_mode"],
                    },
                )
            elif prepared_offer["browser_use_error"] is not None:
                await emit_browser_use_event(
                    session_id=request.session_id,
                    pipeline=request.pipeline,
                    step=request.step,
                    event_type="browser_use_fallback",
                    data={
                        "agent_name": self.slug,
                        "platform": prepared_offer["platform"],
                        "seller": prepared_offer["seller"],
                        "listing_url": prepared_offer["listing_url"],
                        "error": prepared_offer["browser_use_error"],
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
            "browser_use": self.build_runtime_metadata(offers),
        }

    def build_prepared_offer(
        self,
        *,
        listing: dict[str, object],
        median_price: float,
        budget: Any,
        is_top_choice: bool,
    ) -> dict[str, object]:
        platform = str(listing["platform"])
        asking_price = round(float(listing["price"]), 2)
        target_price = self.compute_target_price(
            platform=platform,
            asking_price=asking_price,
            median_price=median_price,
            budget=budget,
        )
        message = self.build_offer_message(
            listing=listing,
            asking_price=asking_price,
            target_price=target_price,
            is_top_choice=is_top_choice,
        )
        return {
            "platform": platform,
            "seller": listing["seller"],
            "listing_url": listing["url"],
            "listing_title": listing["title"],
            "target_price": target_price,
            "message": message,
            "status": "prepared",
            "failure_reason": None,
            "conversation_url": None,
            "execution_mode": "deterministic",
            "browser_use_error": None,
            "attempt_source": "prepared",
            "failure_category": None,
        }

    def compute_target_price(
        self,
        *,
        platform: str,
        asking_price: float,
        median_price: float,
        budget: Any,
    ) -> float:
        discount_anchor = asking_price * self.PLATFORM_DISCOUNTS.get(platform, 0.92)
        market_anchor = max(discount_anchor, median_price * 0.97)
        if isinstance(budget, int | float):
            market_anchor = min(market_anchor, float(budget))
        return round(max(8.0, min(asking_price, market_anchor)), 2)

    def build_offer_message(
        self,
        *,
        listing: dict[str, object],
        asking_price: float,
        target_price: float,
        is_top_choice: bool,
    ) -> str:
        title = str(listing["title"])
        condition = str(listing.get("condition") or "good")
        seller_score = int(listing.get("seller_score", 0))

        if target_price >= asking_price:
            if is_top_choice and seller_score >= 300:
                return (
                    f"Hi! I'm interested in your {title}. It looks like a strong buy, and your seller history gives me "
                    f"confidence. I'm ready to purchase at your asking price of ${asking_price} if it's still available."
                )
            return (
                f"Hi! I'm interested in your {title}. It looks well priced for the market in {condition} condition, "
                f"so I'm ready to buy at your asking price of ${asking_price} if it's still available."
            )

        if seller_score >= 300:
            return (
                f"Hi! I'm interested in your {title}. With its {condition} condition and your strong seller history, "
                f"would you consider ${target_price}? I can pay right away."
            )

        return (
            f"Hi! I'm interested in your {title}. Based on similar sold listings in {condition} condition, "
            f"would you consider ${target_price}? I can pay right away."
        )

    async def try_send_offer(self, prepared_offer: dict[str, object]) -> dict[str, object]:
        platform = str(prepared_offer["platform"])
        profile_path = Path(get_browser_profile_path(platform))
        if not profile_path.exists():
            return {
                "execution_mode": "deterministic",
                "browser_use_error": "profile_missing",
                "attempt_source": "prepared",
                "failure_category": "profile_missing",
            }

        task = build_negotiation_task(
            platform=platform,
            listing_url=str(prepared_offer["listing_url"]),
            message=str(prepared_offer["message"]),
            target_price=float(prepared_offer["target_price"]),
        )
        try:
            result = await run_structured_browser_task(
                task=task,
                output_model=BrowserUseNegotiationResult,
                allowed_domains=self.allowed_domains_for_platform(platform),
                user_data_dir=str(profile_path),
                keep_alive=True,
                max_steps=16,
                max_failures=3,
            )
            return {
                **result,
                "execution_mode": "browser_use",
                "browser_use_error": None,
                "attempt_source": "browser_use",
                "failure_category": None,
            }
        except BrowserUseRuntimeUnavailable as exc:
            return {
                "execution_mode": "deterministic",
                "browser_use_error": classify_browser_use_failure(exc),
                "attempt_source": "prepared",
                "failure_category": classify_browser_use_failure(exc),
            }
        except Exception as exc:
            return {
                "status": "failed",
                "failure_reason": summarize_browser_use_error(exc),
                "conversation_url": None,
                "execution_mode": "browser_use",
                "browser_use_error": classify_browser_use_failure(exc),
                "attempt_source": "browser_use",
                "failure_category": classify_browser_use_failure(exc),
            }

    def allowed_domains_for_platform(self, platform: str) -> list[str]:
        return {
            "depop": ["depop.com", "www.depop.com"],
            "ebay": ["ebay.com", "www.ebay.com"],
            "mercari": ["mercari.com", "www.mercari.com"],
            "offerup": ["offerup.com", "www.offerup.com"],
        }[platform]

    def build_runtime_metadata(self, offers: list[dict[str, object]]) -> dict[str, object]:
        if any(offer["execution_mode"] == "browser_use" for offer in offers):
            live_count = sum(1 for offer in offers if offer["execution_mode"] == "browser_use")
            return build_browser_use_metadata(
                mode="browser_use",
                attempted_live_run=True,
                detail=f"Processed {live_count} live Browser Use negotiation attempts.",
            )
        first_error = next((offer for offer in offers if offer.get("browser_use_error")), None)
        if first_error and first_error["browser_use_error"] == "profile_missing":
            return build_browser_use_metadata(
                mode="skipped",
                attempted_live_run=False,
                error_category="profile_missing",
                detail="Skipped live negotiation because warmed marketplace profiles were missing.",
            )
        return build_browser_use_metadata(
            mode="fallback",
            attempted_live_run=False,
            error_category=first_error["browser_use_error"] if first_error else None,
            detail="Prepared deterministic negotiation offers without live Browser Use sends.",
        )


agent = NegotiationAgent()
app = build_agent_app(agent)
