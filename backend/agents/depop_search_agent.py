from __future__ import annotations

from backend.agents.base import BaseAgent, build_agent_app
from backend.agents.search_support import build_platform_results, detect_brand, detect_item
from backend.schemas import AgentTaskRequest, SearchResultsOutput


class DepopSearchAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            slug="depop_search_agent",
            display_name="Depop Search Agent",
            output_model=SearchResultsOutput,
        )

    async def build_output(self, request: AgentTaskRequest) -> dict:
        query = request.input["original_input"].get("query")
        budget = request.input["original_input"].get("budget")

        results = build_platform_results(platform="depop", query=query, budget=budget)
        brand = detect_brand(query)
        item = detect_item(query)

        return {
            "agent": self.slug,
            "display_name": self.display_name,
            "summary": f"Found {len(results)} Depop listings for {brand} {item}",
            "results": results,
        }


agent = DepopSearchAgent()
app = build_agent_app(agent)
