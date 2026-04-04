from backend.agents.base import StubAgent, build_agent_app
from backend.schemas import DepopListingOutput

agent = StubAgent(
    slug="depop_listing_agent",
    display_name="Depop Listing Agent",
    default_output={
        "title": "Sample Depop Listing",
        "description": "Stub listing generated for scaffold.",
        "suggested_price": 55.0,
        "category_path": "Men/Tops/T-Shirts",
    },
    output_model=DepopListingOutput,
)
app = build_agent_app(agent)
