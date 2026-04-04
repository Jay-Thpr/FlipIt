from backend.agents.base import StubAgent, build_agent_app
from backend.schemas import SearchResultsOutput

agent = StubAgent(
    slug="mercari_search_agent",
    display_name="Mercari Search Agent",
    default_output={
        "results": [
            {
                "platform": "mercari",
                "price": 37.0,
                "title": "Sample listing",
                "url": "https://mercari.example/listing-1",
                "condition": "good",
            }
        ]
    },
    output_model=SearchResultsOutput,
)
app = build_agent_app(agent)
