from __future__ import annotations

from backend.agents.base import BaseAgent, build_agent_app
from backend.agents.browser_use_events import emit_browser_use_event
from backend.agents.browser_use_marketplaces import run_marketplace_search
from backend.agents.browser_use_support import BrowserUseRuntimeUnavailable
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

        results = await self.try_browser_use_search(query=query)
        result_source = "browser_use"
        if results is None:
            results = build_platform_results(platform="mercari", query=query, budget=budget, previous_prices=previous_prices)
            result_source = "fallback"
        brand = detect_brand(query)
        item = detect_item(query)
        await self.emit_listing_found_events(request=request, results=results, result_source=result_source)

        return {
            "agent": self.slug,
            "display_name": self.display_name,
            "summary": f"Found {len(results)} Mercari listings for {brand} {item}",
            "results": results,
        }

    async def try_browser_use_search(self, *, query: str | None) -> list[dict[str, object]] | None:
        if not query:
            return None
        try:
            return await run_marketplace_search("mercari", query)
        except (BrowserUseRuntimeUnavailable, Exception):
            return None

    async def emit_listing_found_events(
        self,
        *,
        request: AgentTaskRequest,
        results: list[dict[str, object]],
        result_source: str,
    ) -> None:
        for index, listing in enumerate(results, start=1):
            await emit_browser_use_event(
                session_id=request.session_id,
                pipeline=request.pipeline,
                step=request.step,
                event_type="listing_found",
                data={
                    "agent_name": self.slug,
                    "platform": listing["platform"],
                    "listing_index": index,
                    "title": listing["title"],
                    "price": listing["price"],
                    "url": listing["url"],
                    "seller": listing["seller"],
                    "posted_at": listing["posted_at"],
                    "source": result_source,
                },
            )


agent = MercariSearchAgent()
app = build_agent_app(agent)
