from backend.agents.base import StubAgent, build_agent_app
from backend.schemas import PricingOutput

agent = StubAgent(
    slug="pricing_agent",
    display_name="Pricing Agent",
    default_output={
        "recommended_list_price": 55.0,
        "expected_profit": 23.0,
        "pricing_confidence": 0.82,
    },
    output_model=PricingOutput,
)
app = build_agent_app(agent)
