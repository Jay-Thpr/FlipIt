# Vision Agent

## Description

Specialized resale item-identification agent for fast inventory triage from short descriptions and image URLs.

## Use Cases

- Identify an item type, brand, category, and condition.
- Convert a rough seller note into structured resale signals.
- Prepare vision output for pricing and listing workflows.

## Example Prompts

- Identify this vintage Nike tee from the photo.
- What kind of jacket is this https://example.com/jacket.jpg
- Tell me the likely brand and condition of this item.

## Input Requirements

- A short description of one item, optional image URLs.

## Output Summary

- Detected item.
- Brand, category, and condition.
- Confidence score and concise identification summary.

## Limitations

- Uses deterministic heuristics, not full computer vision.
- Best on apparel and common resale categories represented in the rules.
- Does not price or list the item by itself.

## Differentiation

Use this agent when the main question is "what is this item?" or "what do I have here?"
