from backend.agents.base import StubAgent, build_agent_app
from backend.schemas import VisionAnalysisOutput

agent = StubAgent(
    slug="vision_agent",
    display_name="Vision Agent",
    default_output={
        "detected_item": "sample item",
        "brand": "unknown",
        "category": "apparel",
        "condition": "good",
    },
    output_model=VisionAnalysisOutput,
)
app = build_agent_app(agent)
