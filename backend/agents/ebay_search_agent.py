from __future__ import annotations

from backend.agents.base import BaseAgent, build_agent_app
from backend.agents.browser_use_events import emit_browser_use_event
from backend.agents.browser_use_marketplaces import run_marketplace_search
from backend.agents.browser_use_support import (
    BrowserUseRuntimeUnavailable,
    build_browser_use_metadata,
    classify_browser_use_failure,
)
from backend.agents.httpx_clients import search_ebay_browse_api
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

        # Priority: eBay Browse API → Browser Use → deterministic fallback
        results, result_source, browser_use_error = await self._resolve_results(query=query)
        if results is None:
            results = build_platform_results(platform="ebay", query=query, budget=budget, previous_prices=depop_prices)
            result_source = "fallback"
            if browser_use_error is not None:
                await self.emit_fallback_event(request=request, error=browser_use_error)
        brand = detect_brand(query)
        item = detect_item(query)
        await self.emit_listing_found_events(request=request, results=results, result_source=result_source)

        return {
            "agent": self.slug,
            "display_name": self.display_name,
            "summary": f"Found {len(results)} eBay listings for {brand} {item}",
            "results": results,
            "execution_mode": result_source,
            "browser_use_error": browser_use_error,
            "browser_use": self.build_runtime_metadata(
                query=query,
                result_source=result_source,
                browser_use_error=browser_use_error,
                result_count=len(results),
            ),
        }

    async def _resolve_results(
        self, *, query: str | None
    ) -> tuple[list[dict[str, object]] | None, str, str | None]:
        if not query:
            return None, "fallback", None

        # 1. Try eBay Browse API first (official, fast, no Chromium)
        api_results = await search_ebay_browse_api(query)
        if api_results is not None:
            return api_results, "httpx", None

        # 2. Fall through to Browser Use
        try:
            bu_results = await run_marketplace_search("ebay", query)
            return bu_results, "browser_use", None
        except (BrowserUseRuntimeUnavailable, Exception) as exc:
            return None, "fallback", classify_browser_use_failure(exc)

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

    async def emit_fallback_event(self, *, request: AgentTaskRequest, error: str) -> None:
        await emit_browser_use_event(
            session_id=request.session_id,
            pipeline=request.pipeline,
            step=request.step,
            event_type="browser_use_fallback",
            data={
                "agent_name": self.slug,
                "platform": "ebay",
                "error": error,
            },
        )

    def build_runtime_metadata(
        self,
        *,
        query: str | None,
        result_source: str,
        browser_use_error: str | None,
        result_count: int,
    ) -> dict[str, object]:
        if not query:
            return build_browser_use_metadata(
                mode="skipped",
                attempted_live_run=False,
                detail="Skipped Browser Use search because no query was provided.",
            )
        if result_source == "browser_use":
            return build_browser_use_metadata(
                mode="browser_use",
                attempted_live_run=True,
                detail=f"Live Browser Use search returned {result_count} eBay listings.",
            )
        attempted_live_run = browser_use_error not in {None, "runtime_unavailable"}
        return build_browser_use_metadata(
            mode="fallback",
            attempted_live_run=attempted_live_run,
            error_category=browser_use_error,
            detail="Used deterministic fallback results for eBay search.",
        )


agent = EbaySearchAgent()
app = build_agent_app(agent)
