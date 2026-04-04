from backend.agents.base import StubAgent, build_agent_app
from backend.schemas import NegotiationOutput

agent = StubAgent(
    slug="negotiation_agent",
    display_name="Negotiation Agent",
    default_output={
        "offer_messages": [
            {
                "platform": "offerup",
                "listing_title": "Sample ranked listing",
                "target_price": 32.0,
                "message": "Hi, would you take $32?",
            }
        ]
    },
    output_model=NegotiationOutput,
)
app = build_agent_app(agent)
