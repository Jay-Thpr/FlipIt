from __future__ import annotations

import copy

from backend.item_schemas import Conversation, Item, ItemCreateRequest, Message, new_item_id


SELL_COLOR = "#6EE7B7"
BUY_COLOR = "#FCD34D"

_DEFAULT_ITEMS: list[dict] = [
    {
        "id": "1",
        "type": "sell",
        "name": "Air Jordan 1 Retro High OG",
        "description": "Chicago colorway, DS (deadstock). Box included. Size 10.",
        "condition": "New",
        "imageColor": "#FCA5A5",
        "targetPrice": 320,
        "minPrice": 260,
        "maxPrice": 380,
        "autoAcceptThreshold": 300,
        "platforms": ["depop", "ebay", "mercari"],
        "status": "active",
        "quantity": 1,
        "negotiationStyle": "moderate",
        "replyTone": "professional",
        "bestOffer": 295,
        "photos": [
            "https://picsum.photos/seed/jordan1a/400/400",
            "https://picsum.photos/seed/jordan1b/400/400",
        ],
        "marketData": [
            {"platform": "depop", "bestBuyPrice": 299, "bestSellPrice": 315, "volume": 42},
            {"platform": "ebay", "bestBuyPrice": 310, "bestSellPrice": 332, "volume": 128},
        ],
        "conversations": [
            {
                "id": "c1",
                "username": "sneaker_kylie",
                "platform": "depop",
                "lastMessage": "Would you take $280?",
                "timestamp": "2m ago",
                "unread": True,
                "messages": [
                    {"id": "m1", "sender": "them", "text": "Hey! Love these. Are they still available?", "timestamp": "10:32 AM"},
                    {"id": "m2", "sender": "agent", "text": "Hi! Yes, still available.", "timestamp": "10:33 AM"},
                ],
            }
        ],
    },
    {
        "id": "4",
        "type": "buy",
        "name": "Canon AE-1 Program",
        "description": "Looking for a clean body with working meter and shutter. Black preferred.",
        "condition": "Good",
        "imageColor": "#FCD34D",
        "targetPrice": 85,
        "minPrice": 60,
        "maxPrice": 120,
        "autoAcceptThreshold": 90,
        "platforms": ["ebay", "depop", "mercari", "offerup"],
        "status": "active",
        "quantity": 1,
        "negotiationStyle": "aggressive",
        "replyTone": "professional",
        "bestOffer": 95,
        "photos": [],
        "marketData": [
            {"platform": "ebay", "bestBuyPrice": 85, "bestSellPrice": 98, "volume": 87},
            {"platform": "depop", "bestBuyPrice": 95, "bestSellPrice": 110, "volume": 31},
        ],
        "conversations": [
            {
                "id": "c4",
                "username": "vintage_photo_co",
                "platform": "depop",
                "lastMessage": "I can do $95 shipped.",
                "timestamp": "15m ago",
                "unread": True,
                "messages": [
                    {"id": "m1", "sender": "agent", "text": "Would you consider $75 shipped?", "timestamp": "10:45 AM"},
                    {"id": "m2", "sender": "them", "text": "I can do $95 shipped.", "timestamp": "11:18 AM"},
                ],
            }
        ],
    },
]


class ItemStore:
    def __init__(self) -> None:
        self._items: dict[str, Item] = {}
        self.reset()

    def reset(self) -> None:
        self._items = {
            item["id"]: Item.model_validate(copy.deepcopy(item))
            for item in _DEFAULT_ITEMS
        }

    def list_items(self, item_type: str | None = None) -> list[Item]:
        items = list(self._items.values())
        if item_type:
            items = [item for item in items if item.type == item_type]
        return items

    def get_item(self, item_id: str) -> Item | None:
        return self._items.get(item_id)

    def get_conversation(self, item_id: str, conversation_id: str) -> Conversation | None:
        item = self.get_item(item_id)
        if item is None:
            return None
        for conversation in item.conversations:
            if conversation.id == conversation_id:
                return conversation
        return None

    def create_item(self, request: ItemCreateRequest) -> Item:
        item = Item(
            id=new_item_id(),
            type=request.type,
            name=request.name,
            description=request.description,
            condition=request.condition,
            imageColor=SELL_COLOR if request.type == "sell" else BUY_COLOR,
            targetPrice=request.targetPrice,
            minPrice=request.minPrice,
            maxPrice=request.maxPrice,
            autoAcceptThreshold=request.autoAcceptThreshold,
            platforms=request.platforms,
            status="active" if request.aiActive else "paused",
            quantity=request.quantity,
            negotiationStyle=request.negotiationStyle,
            replyTone=request.replyTone,
            bestOffer=None,
            photos=request.photos,
            marketData=[],
            conversations=[],
        )
        self._items[item.id] = item
        return item


item_store = ItemStore()
