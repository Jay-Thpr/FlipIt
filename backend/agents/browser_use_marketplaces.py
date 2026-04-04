from __future__ import annotations

from typing import Literal
from urllib.parse import quote_plus

from pydantic import BaseModel, Field

from backend.agents.browser_use_support import run_structured_browser_task

Marketplace = Literal["depop", "ebay", "mercari", "offerup"]


class BrowserUseSearchListing(BaseModel):
    title: str
    price: float
    url: str
    condition: str
    seller: str
    seller_score: int = 0
    posted_at: str


class BrowserUseSearchResult(BaseModel):
    results: list[BrowserUseSearchListing] = Field(default_factory=list)


class BrowserUseListingDraftResult(BaseModel):
    draft_status: str
    form_screenshot_url: str | None = None


class BrowserUseNegotiationResult(BaseModel):
    status: str
    failure_reason: str | None = None
    conversation_url: str | None = None


def build_marketplace_search_url(platform: Marketplace, query: str) -> str:
    encoded_query = quote_plus(query)
    if platform == "depop":
        return f"https://www.depop.com/search/?q={encoded_query}"
    if platform == "ebay":
        return f"https://www.ebay.com/sch/i.html?_nkw={encoded_query}&LH_BIN=1&_ipg=24"
    if platform == "mercari":
        return f"https://www.mercari.com/search/?keyword={encoded_query}"
    return f"https://offerup.com/search?q={encoded_query}"


def build_marketplace_search_task(platform: Marketplace, query: str, max_results: int = 10) -> str:
    url = build_marketplace_search_url(platform, query)
    platform_label = {"depop": "Depop", "ebay": "eBay", "mercari": "Mercari", "offerup": "OfferUp"}[platform]
    return f"""
Navigate directly to: {url}
Wait for active listing results to render.
Extract up to {max_results} visible listings for the query "{query}".
For each listing return:
- title
- price as a number in USD
- url
- condition
- seller username or display name
- seller_score as an integer (review count, feedback score, or rating count). Use 0 if unavailable.
- posted_at in YYYY-MM-DD format. If the site only shows relative recency, convert it to a best-effort ISO date.
Only include active listings with a visible price and URL.
Return only JSON matching the schema.
"""


async def run_marketplace_search(platform: Marketplace, query: str, max_results: int = 10) -> list[dict[str, object]]:
    result = await run_structured_browser_task(
        task=build_marketplace_search_task(platform, query, max_results=max_results),
        output_model=BrowserUseSearchResult,
        allowed_domains={
            "depop": ["depop.com", "www.depop.com"],
            "ebay": ["ebay.com", "www.ebay.com"],
            "mercari": ["mercari.com", "www.mercari.com"],
            "offerup": ["offerup.com", "www.offerup.com"],
        }[platform],
        max_steps=12,
        max_failures=3,
    )
    return [
        {
            "platform": platform,
            **listing,
        }
        for listing in result["results"]
    ]


def build_depop_listing_task(
    *,
    title: str,
    description: str,
    suggested_price: float,
    category_path: str,
    image_path: str | None,
) -> str:
    image_instruction = (
        f'Upload the local file at path "{image_path}" as the first listing photo.'
        if image_path
        else "Skip photo upload because no local image path was provided."
    )
    return f"""
Navigate directly to https://www.depop.com/sell or the Depop listing creation flow.
Use the existing logged-in browser profile session.
{image_instruction}
Populate the listing form without submitting it.
Set the category using this path if possible: {category_path}
Fill the title exactly as: {title}
Fill the description exactly as: {description}
Set the price to: {suggested_price}
Stop before the final publish or submit action.
Return only JSON matching the schema with:
- draft_status set to "ready" if the form is populated
- form_screenshot_url as a descriptive artifact string if a screenshot URL/path is available, otherwise null
"""


def build_negotiation_task(*, platform: str, listing_url: str, message: str, target_price: float) -> str:
    return f"""
Navigate directly to: {listing_url}
Use the existing logged-in browser profile session.
Open the seller contact or offer flow for this listing.
Send this message exactly:
{message}
If the platform supports a numeric offer price, set it to {target_price}.
Return only JSON matching the schema with:
- status as "sent" if the message was submitted, otherwise "failed"
- failure_reason with a short explanation when status is "failed"
- conversation_url if the platform exposes a conversation or offer thread URL, otherwise null
"""
