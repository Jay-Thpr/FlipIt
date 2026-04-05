from __future__ import annotations


def test_list_items_returns_seeded_items(client) -> None:
    response = client.get("/items")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 2
    assert {item["type"] for item in payload} == {"sell", "buy"}


def test_list_items_supports_type_filter(client) -> None:
    response = client.get("/items", params={"type": "sell"})

    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert all(item["type"] == "sell" for item in payload)


def test_get_item_returns_frontend_shape(client) -> None:
    response = client.get("/items/1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Air Jordan 1 Retro High OG"
    assert isinstance(payload["photos"], list)
    assert isinstance(payload["marketData"], list)
    assert isinstance(payload["conversations"], list)


def test_get_conversation_returns_nested_conversation(client) -> None:
    response = client.get("/items/1/conversations/c1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["username"] == "sneaker_kylie"
    assert payload["messages"][0]["sender"] in {"agent", "them"}


def test_create_item_matches_new_listing_screen_fields(client) -> None:
    response = client.post(
        "/items",
        json={
            "type": "sell",
            "name": "Patagonia Synchilla",
            "description": "Blue fleece jacket",
            "condition": "Good",
            "targetPrice": 88,
            "minPrice": 65,
            "maxPrice": 110,
            "autoAcceptThreshold": 90,
            "platforms": ["depop", "ebay"],
            "quantity": 1,
            "negotiationStyle": "moderate",
            "replyTone": "professional",
            "aiActive": True,
            "photos": ["https://example.com/photo-1.jpg"],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "Patagonia Synchilla"
    assert payload["status"] == "active"
    assert payload["platforms"] == ["depop", "ebay"]
    assert payload["photos"] == ["https://example.com/photo-1.jpg"]
    assert payload["marketData"] == []
    assert payload["conversations"] == []
