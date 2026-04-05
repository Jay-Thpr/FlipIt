# Resale Copilot Agent

## Description

Agentverse-facing resale copilot for broad flipping workflows. This agent routes a natural-language request into the right specialist path for identifying an item, pricing it, creating a Depop draft, ranking buying opportunities, or preparing negotiation.

## Use Cases

- Help a seller figure out what an item is and whether it is worth listing.
- Route a vague "help me flip this" prompt into the right resale workflow.
- Turn a resale sourcing request into ranked marketplace results.

## Example Prompts

- Help me flip this vintage Nike tee.
- Find the best place to buy this Carhartt jacket under $80.
- Turn this item into a Depop draft.

## Input Requirements

- A natural-language resale request.
- Optional image URLs.
- Optional budget or marketplace preferences.

## Output Summary

- Chosen task family.
- Specialist agent used.
- Structured workflow result from the backend resale pipeline.

## Limitations

- Routes requests with lightweight heuristics rather than a full planning model.
- Depends on the backend specialist agents for final execution quality.
- Live marketplace actions still depend on local Browser Use prerequisites.

## Differentiation

Use this agent when the user intent is broad or ambiguous. Use the specialist agents directly when the task is already clearly scoped.
