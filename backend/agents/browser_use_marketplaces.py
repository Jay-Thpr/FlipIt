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


class BrowserUseListingCheckpointResult(BaseModel):
    listing_status: str
    ready_for_confirmation: bool = False
    draft_status: str | None = None
    draft_url: str | None = None
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


def build_depop_listing_prepare_task(
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
Use a desktop or non-mobile listing layout if the site offers multiple device experiences.
{image_instruction}
Populate the entire listing form without submitting it.
Set the category using this path if possible: {category_path}
Fill the title exactly as: {title}
Fill the description exactly as: {description}
Set the price to: {suggested_price}
Stop at the final publish or submit action and do not click it.
Return only JSON matching the schema with:
- listing_status set to "ready_for_confirmation" if the form is populated and ready for final review
- ready_for_confirmation set to true when the form is populated and waiting on user approval
- draft_status set to "ready" if the form is populated
- draft_url set to the in-progress draft URL if the page exposes one, otherwise null
- form_screenshot_url as a descriptive artifact string if a screenshot URL/path is available, otherwise null
Treat the "ready_for_confirmation" state as a deterministic review checkpoint.
Never click the final publish or submit button during this prepare phase.
"""


def build_depop_listing_task(
    *,
    title: str,
    description: str,
    suggested_price: float,
    category_path: str,
    image_path: str | None,
) -> str:
    return build_depop_listing_prepare_task(
        title=title,
        description=description,
        suggested_price=suggested_price,
        category_path=category_path,
        image_path=image_path,
    )


def build_depop_listing_revision_task(
    *,
    revision_instructions: str,
    title: str | None = None,
    description: str | None = None,
    suggested_price: float | None = None,
    category_path: str | None = None,
) -> str:
    baseline_instructions = ""
    if all(value is not None for value in (title, description, suggested_price, category_path)):
        baseline_instructions = f"""
Preserve any fields the user did not ask to change.
Keep the draft aligned to these baseline values unless the revision request overrides them:
- title: {title}
- description: {description}
- price: {suggested_price}
- category path: {category_path}
"""

    return f"""
Navigate directly to https://www.depop.com/sell or the active Depop listing creation flow.
Use the existing logged-in browser profile session.
Use a desktop or non-mobile listing layout if the site offers multiple device experiences.
Find the existing in-progress listing form or draft.
Apply these revision instructions to the current form:
{revision_instructions}
{baseline_instructions}
Do not submit or publish the listing.
Stop once the form reflects the requested changes and is ready for review.
Return only JSON matching the schema with:
- listing_status set to "ready_for_confirmation" if the revised form is ready for final review
- ready_for_confirmation set to true when the revised form is populated and waiting on user approval
- draft_status set to "ready" if the form remains populated
- draft_url set to the in-progress draft URL if the page exposes one, otherwise null
- form_screenshot_url as a descriptive artifact string if a screenshot URL/path is available, otherwise null
Treat the end state as the same deterministic review checkpoint and do not publish the listing.
"""


def build_depop_listing_submit_task() -> str:
    return """
Navigate directly to https://www.depop.com/sell or the active Depop listing creation flow.
Use the existing logged-in browser profile session.
Use a desktop or non-mobile listing layout if the site offers multiple device experiences.
Find the prepared in-progress listing form or draft.
Verify the listing is fully populated, then perform the final publish or submit action.
Return only JSON matching the schema with:
- listing_status set to "submitted" if the listing was published successfully
- ready_for_confirmation set to false
- draft_status set to "submitted"
- draft_url set to null unless the marketplace exposes a stable submitted listing URL in the same flow
- form_screenshot_url as a descriptive artifact string if a confirmation artifact URL/path is available, otherwise null
"""


def build_depop_listing_abort_task() -> str:
    return """
Navigate directly to https://www.depop.com/sell or the active Depop listing creation flow.
Use the existing logged-in browser profile session.
Use a desktop or non-mobile listing layout if the site offers multiple device experiences.
Find the prepared in-progress listing form or draft.
Close, discard, or otherwise abandon the draft without publishing it.
Return only JSON matching the schema with:
- listing_status set to "aborted" if the draft was abandoned or the browser was left without publishing
- ready_for_confirmation set to false
- draft_status set to "aborted"
- draft_url set to null after the draft is abandoned
- form_screenshot_url as a descriptive artifact string if a confirmation artifact URL/path is available, otherwise null
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
