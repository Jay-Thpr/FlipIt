from __future__ import annotations

from backend.agents.base import BaseAgent, build_agent_app
from backend.agents.browser_use_marketplaces import run_marketplace_search
from backend.agents.browser_use_support import BrowserUseRuntimeUnavailable
from backend.agents.search_support import build_platform_results, detect_brand, detect_item
from backend.schemas import AgentTaskRequest, SearchResultsOutput


class EbaySearchAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            slug="ebay_search_agent",
            display_name="eBay Search Agent",
            output_model=SearchResultsOutput,
        )

    async def build_output(self, request: AgentTaskRequest) -> dict:
        query = request.input["original_input"].get("query")
        budget = request.input["original_input"].get("budget")
        depop_results = request.input["previous_outputs"]["depop_search"]["results"]
        depop_prices = [listing["price"] for listing in depop_results]

        results = await self.try_browser_use_search(query=query)
        if results is None:
            results = build_platform_results(platform="ebay", query=query, budget=budget, previous_prices=depop_prices)
        brand = detect_brand(query)
        item = detect_item(query)

        return {
            "agent": self.slug,
            "display_name": self.display_name,
            "summary": f"Found {len(results)} eBay listings for {brand} {item}",
            "results": results,
        }

    async def try_browser_use_search(self, *, query: str | None) -> list[dict[str, object]] | None:
        if not query:
            return None
        try:
            return await run_marketplace_search("ebay", query)
        except (BrowserUseRuntimeUnavailable, Exception):
            return None


agent = EbaySearchAgent()
app = build_agent_app(agent)
