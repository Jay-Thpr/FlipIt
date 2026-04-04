from __future__ import annotations

from backend.agents.base import BaseAgent, build_agent_app
from backend.schemas import AgentTaskRequest, DepopListingOutput


class DepopListingAgent(BaseAgent):
    CATEGORY_PATHS = {
        "hoodie": "Men/Tops/Hoodies",
        "jacket": "Men/Outerwear/Jackets",
        "tee": "Men/Tops/T-Shirts",
        "t-shirt": "Men/Tops/T-Shirts",
        "sweater": "Men/Tops/Sweaters",
        "shirt": "Men/Tops/Shirts",
        "pants": "Men/Bottoms/Pants",
        "jeans": "Men/Bottoms/Jeans",
        "shorts": "Men/Bottoms/Shorts",
        "dress": "Women/Dresses",
        "skirt": "Women/Bottoms/Skirts",
        "bag": "Accessories/Bags",
        "hat": "Accessories/Hats",
        "shoes": "Shoes",
        "sneakers": "Shoes/Sneakers",
    }

    def __init__(self) -> None:
        super().__init__(
            slug="depop_listing_agent",
            display_name="Depop Listing Agent",
            output_model=DepopListingOutput,
        )

    async def build_output(self, request: AgentTaskRequest) -> dict:
        original_input = request.input["original_input"]
        previous_outputs = request.input["previous_outputs"]

        vision_analysis = previous_outputs["vision_analysis"]
        sold_comps = previous_outputs["ebay_sold_comps"]
        pricing = previous_outputs["pricing"]

        brand = vision_analysis["brand"]
        detected_item = vision_analysis["detected_item"]
        condition = vision_analysis["condition"]
        notes = (original_input.get("notes") or "").strip()

        descriptor = f"{brand} {detected_item}".strip() if brand != "Unknown" else detected_item.title()
        title = f"{descriptor} - {condition.title()} Condition"
        category_path = self.CATEGORY_PATHS.get(detected_item.lower(), "Men/Tops/T-Shirts")
        suggested_price = pricing["recommended_list_price"]

        note_sentence = notes if notes else f"Clean {detected_item} ready to list."
        description = (
            f"{descriptor} in {condition} condition. {note_sentence} "
            f"Suggested list price: ${suggested_price}. "
            f"Recent eBay sold range: ${sold_comps['low_sold_price']}-${sold_comps['high_sold_price']} "
            f"across {sold_comps['sample_size']} comps. "
            f"Estimated profit: ${pricing['expected_profit']}."
        )

        return {
            "agent": self.slug,
            "display_name": self.display_name,
            "summary": f"Prepared Depop listing for {descriptor} at ${suggested_price}",
            "title": title,
            "description": description,
            "suggested_price": suggested_price,
            "category_path": category_path,
        }


agent = DepopListingAgent()
app = build_agent_app(agent)
