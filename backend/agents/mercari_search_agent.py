from __future__ import annotations

from backend.agents.base import BaseAgent, build_agent_app
from backend.agents.search_support import build_platform_results, detect_brand, detect_item
from backend.schemas import AgentTaskRequest, SearchResultsOutput


class MercariSearchAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            slug="mercari_search_agent",
            display_name="Mercari Search Agent",
            output_model=SearchResultsOutput,
        )

    async def build_output(self, request: AgentTaskRequest) -> dict:
        query = request.input["original_input"].get("query")
        budget = request.input["original_input"].get("budget")
        previous_outputs = request.input["previous_outputs"]
        previous_prices = [
            listing["price"]
            for output in (previous_outputs["depop_search"], previous_outputs["ebay_search"])
            for listing in output["results"]
        ]

        results = build_platform_results(platform="mercari", query=query, budget=budget, previous_prices=previous_prices)
        brand = detect_brand(query)
        item = detect_item(query)

        return {
            "agent": self.slug,
            "display_name": self.display_name,
            "summary": f"Found {len(results)} Mercari listings for {brand} {item}",
            "results": results,
        }


agent = MercariSearchAgent()
app = build_agent_app(agent)
