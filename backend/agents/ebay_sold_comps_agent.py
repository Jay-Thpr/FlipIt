from backend.agents.base import StubAgent, build_agent_app
from backend.schemas import EbaySoldCompsOutput

agent = StubAgent(
    slug="ebay_sold_comps_agent",
    display_name="eBay Sold Comps Agent",
    default_output={
        "median_sold_price": 42.0,
        "low_sold_price": 28.0,
        "high_sold_price": 58.0,
        "sample_size": 12,
    },
    output_model=EbaySoldCompsOutput,
)
app = build_agent_app(agent)
