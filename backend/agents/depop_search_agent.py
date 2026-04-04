from backend.agents.base import StubAgent, build_agent_app
from backend.schemas import SearchResultsOutput

agent = StubAgent(
    slug="depop_search_agent",
    display_name="Depop Search Agent",
    default_output={
        "results": [
            {
                "platform": "depop",
                "price": 40.0,
                "title": "Sample listing",
                "url": "https://depop.example/listing-1",
                "condition": "good",
            }
        ]
    },
    output_model=SearchResultsOutput,
)
app = build_agent_app(agent)
