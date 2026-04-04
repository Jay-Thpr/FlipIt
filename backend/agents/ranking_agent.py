from backend.agents.base import StubAgent, build_agent_app
from backend.schemas import RankingOutput

agent = StubAgent(
    slug="ranking_agent",
    display_name="Ranking Agent",
    default_output={
        "top_choice": {
            "platform": "offerup",
            "title": "Sample ranked listing",
            "price": 36.0,
            "score": 0.91,
            "reason": "Lowest price with strong condition match",
        },
        "candidate_count": 4,
    },
    output_model=RankingOutput,
)
app = build_agent_app(agent)
