from backend.agents.base import StubAgent, build_agent_app
from backend.schemas import SearchResultsOutput

agent = StubAgent(
    slug="ebay_search_agent",
    display_name="eBay Search Agent",
    default_output={
        "results": [
            {
                "platform": "ebay",
                "price": 38.0,
                "title": "Sample listing",
                "url": "https://ebay.example/listing-1",
                "condition": "good",
            }
        ]
    },
    output_model=SearchResultsOutput,
)
app = build_agent_app(agent)
