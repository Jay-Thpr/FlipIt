from backend.agents.base import StubAgent, build_agent_app
from backend.schemas import SearchResultsOutput

agent = StubAgent(
    slug="offerup_search_agent",
    display_name="OfferUp Search Agent",
    default_output={
        "results": [
            {
                "platform": "offerup",
                "price": 36.0,
                "title": "Sample listing",
                "url": "https://offerup.example/listing-1",
                "condition": "good",
            }
        ]
    },
    output_model=SearchResultsOutput,
)
app = build_agent_app(agent)
