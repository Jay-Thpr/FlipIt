from __future__ import annotations

from typing import Iterable


KNOWN_BRANDS = {
    "nike": "Nike",
    "adidas": "Adidas",
    "patagonia": "Patagonia",
    "carhartt": "Carhartt",
    "levi's": "Levi's",
    "levis": "Levi's",
    "stussy": "Stussy",
}

KNOWN_ITEMS = {
    "hoodie": "hoodie",
    "jacket": "jacket",
    "tee": "tee",
    "shirt": "shirt",
    "sweatshirt": "sweatshirt",
    "crewneck": "crewneck",
    "jeans": "jeans",
    "pants": "pants",
    "shorts": "shorts",
    "sneakers": "sneakers",
}

CONDITION_BY_PLATFORM = {
    "depop": "great",
    "ebay": "good",
    "mercari": "excellent",
    "offerup": "good",
}

PLATFORM_PRICE_OFFSETS = {
    "depop": 1.02,
    "ebay": 0.94,
    "mercari": 0.97,
    "offerup": 0.88,
}


def tokenize_query(query: str | None) -> list[str]:
    return (query or "").replace("/", " ").replace("-", " ").lower().split()


def detect_brand(query: str | None) -> str:
    tokens = tokenize_query(query)
    for token in tokens:
        if token in KNOWN_BRANDS:
            return KNOWN_BRANDS[token]
    return "Vintage"


def detect_item(query: str | None) -> str:
    tokens = tokenize_query(query)
    for token in tokens:
        if token in KNOWN_ITEMS:
            return KNOWN_ITEMS[token]
    return "item"


def detect_size(query: str | None) -> str | None:
    tokens = tokenize_query(query)
    for index, token in enumerate(tokens):
        if token == "size" and index + 1 < len(tokens):
            return tokens[index + 1].upper()
        if token.upper() in {"XS", "S", "M", "L", "XL", "XXL"}:
            return token.upper()
    return None


def build_listing_title(*, brand: str, item: str, size: str | None, platform_label: str, ordinal: int) -> str:
    size_fragment = f" size {size}" if size else ""
    if item == "item":
        return f"{brand} resale find{size_fragment} #{ordinal} on {platform_label}"
    return f"{brand} {item}{size_fragment} #{ordinal} on {platform_label}"


def build_listing_url(platform: str, brand: str, item: str, ordinal: int) -> str:
    slug = f"{brand}-{item}-{ordinal}".lower().replace(" ", "-").replace("'", "")
    return f"https://{platform}.example/{slug}"


def derive_base_price(query: str | None, budget: float | None, previous_prices: Iterable[float] = ()) -> float:
    tokens = tokenize_query(query)
    token_bonus = min(len(tokens), 8) * 0.75
    budget_anchor = budget if budget is not None else 44.0
    prices = list(previous_prices)
    if prices:
        baseline = sum(prices) / len(prices)
    else:
        baseline = budget_anchor
    return round(max(18.0, min(budget_anchor, baseline) - 3.5 + token_bonus), 2)


def build_platform_results(
    *,
    platform: str,
    query: str | None,
    budget: float | None,
    previous_prices: Iterable[float] = (),
) -> list[dict[str, object]]:
    brand = detect_brand(query)
    item = detect_item(query)
    size = detect_size(query)
    platform_label = platform.title() if platform != "ebay" else "eBay"

    base_price = derive_base_price(query, budget, previous_prices)
    platform_price = round(base_price * PLATFORM_PRICE_OFFSETS[platform], 2)
    second_price = round(platform_price + 4.5, 2)
    condition = CONDITION_BY_PLATFORM[platform]

    return [
        {
            "platform": platform,
            "title": build_listing_title(brand=brand, item=item, size=size, platform_label=platform_label, ordinal=1),
            "price": platform_price,
            "url": build_listing_url(platform, brand, item, 1),
            "condition": condition,
        },
        {
            "platform": platform,
            "title": build_listing_title(brand=brand, item=item, size=size, platform_label=platform_label, ordinal=2),
            "price": second_price,
            "url": build_listing_url(platform, brand, item, 2),
            "condition": "good" if condition == "excellent" else condition,
        },
    ]
