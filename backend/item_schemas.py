from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


Platform = Literal["ebay", "depop", "mercari", "offerup", "facebook"]
ItemStatus = Literal["active", "paused", "archived"]
ItemType = Literal["buy", "sell"]
NegotiationStyle = Literal["aggressive", "moderate", "passive"]
ReplyTone = Literal["professional", "casual", "firm"]
MessageSender = Literal["agent", "them"]


class Message(BaseModel):
    id: str
    sender: MessageSender
    text: str
    timestamp: str


class Conversation(BaseModel):
    id: str
    username: str
    platform: Platform
    lastMessage: str
    timestamp: str
    unread: bool
    messages: list[Message] = Field(default_factory=list)


class MarketData(BaseModel):
    platform: Platform
    bestBuyPrice: float
    bestSellPrice: float
    volume: int


class Item(BaseModel):
    id: str
    type: ItemType
    name: str
    description: str
    condition: str
    imageColor: str
    targetPrice: float
    minPrice: float | None = None
    maxPrice: float | None = None
    autoAcceptThreshold: float | None = None
    platforms: list[Platform] = Field(default_factory=list)
    status: ItemStatus
    quantity: int = 1
    negotiationStyle: NegotiationStyle
    replyTone: ReplyTone
    bestOffer: float | None = None
    photos: list[str] = Field(default_factory=list)
    marketData: list[MarketData] = Field(default_factory=list)
    conversations: list[Conversation] = Field(default_factory=list)


class ItemCreateRequest(BaseModel):
    type: ItemType
    name: str
    description: str = ""
    condition: str = "Good"
    targetPrice: float
    minPrice: float | None = None
    maxPrice: float | None = None
    autoAcceptThreshold: float | None = None
    platforms: list[Platform] = Field(default_factory=list)
    quantity: int = 1
    negotiationStyle: NegotiationStyle = "moderate"
    replyTone: ReplyTone = "professional"
    aiActive: bool = True
    photos: list[str] = Field(default_factory=list)


class ItemCreateResponse(Item):
    pass


def new_item_id() -> str:
    return str(uuid4())
