from __future__ import annotations

from backend.agents.base import BaseAgent, build_agent_app
from backend.schemas import AgentTaskRequest, RankingOutput


class RankingAgent(BaseAgent):
    CONDITION_SCORES = {
        "excellent": 1.0,
        "great": 0.93,
        "good": 0.84,
        "fair": 0.68,
    }

    PLATFORM_BONUSES = {
        "mercari": 0.04,
        "offerup": 0.05,
        "ebay": 0.02,
        "depop": 0.01,
    }

    def __init__(self) -> None:
        super().__init__(
            slug="ranking_agent",
            display_name="Ranking Agent",
            output_model=RankingOutput,
        )

    def score_listing(self, listing: dict[str, object], budget: float | None) -> float:
        price = float(listing["price"])
        condition = str(listing["condition"])
        platform = str(listing["platform"])

        if budget is None:
            price_fit = 0.9
        else:
            price_fit = max(0.0, 1 - abs(budget - price) / max(budget, 1.0))

        score = (
            0.56 * price_fit
            + 0.34 * self.CONDITION_SCORES.get(condition, 0.75)
            + self.PLATFORM_BONUSES.get(platform, 0.0)
        )
        return round(min(0.99, score), 2)

    async def build_output(self, request: AgentTaskRequest) -> dict:
        budget = request.input["original_input"].get("budget")
        previous_outputs = request.input["previous_outputs"]
        candidates = [
            listing
            for step in ("depop_search", "ebay_search", "mercari_search", "offerup_search")
            for listing in previous_outputs[step]["results"]
        ]

        ranked_candidates = []
        for listing in candidates:
            score = self.score_listing(listing, budget)
            ranked_candidates.append(
                {
                    "platform": listing["platform"],
                    "title": listing["title"],
                    "price": listing["price"],
                    "score": score,
                    "reason": f"{listing['condition'].title()} condition with strong budget fit on {listing['platform']}",
                }
            )

        ranked_candidates.sort(key=lambda item: (-item["score"], item["price"], item["title"]))
        top_choice = ranked_candidates[0]

        return {
            "agent": self.slug,
            "display_name": self.display_name,
            "summary": f"Ranked {len(ranked_candidates)} listings and selected {top_choice['platform']} as the top choice",
            "top_choice": top_choice,
            "candidate_count": len(ranked_candidates),
        }


agent = RankingAgent()
app = build_agent_app(agent)
