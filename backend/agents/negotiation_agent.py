from __future__ import annotations

from backend.agents.base import BaseAgent, build_agent_app
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
            }
        ]
        for listing in all_candidates:
            if listing["title"] in prioritized_titles:
                continue
            prioritized_candidates.append(listing)
            prioritized_titles.add(listing["title"])
            if len(prioritized_candidates) == 3:
                break

        offer_messages = []
        for listing in prioritized_candidates:
            platform = listing["platform"]
            target_price = round(float(listing["price"]) * self.PLATFORM_DISCOUNTS.get(platform, 0.92), 2)
            offer_messages.append(
                {
                    "platform": platform,
                    "listing_title": listing["title"],
                    "target_price": target_price,
                    "message": (
                        f"Hi! I love this listing. Would you consider ${target_price} "
                        f"for {listing['title']}?"
                    ),
                }
            )

        return {
            "agent": self.slug,
            "display_name": self.display_name,
            "summary": f"Prepared {len(offer_messages)} negotiation messages starting with {top_choice['platform']}",
            "offer_messages": offer_messages,
        }


agent = NegotiationAgent()
app = build_agent_app(agent)
