# Nano Banana Handoff

This file is the ownership map for the Nano Banana portion of the backend.

## Your Scope

- clean-photo generation provider integration
- request payload shape for Nano Banana
- response parsing for the generated photo URL
- local mock service support
- prompt text for resale-ready white-background output

## Files You Now Own

- [README.md](README.md)
- [client.py](client.py)
- [prompts.py](prompts.py)
- [__init__.py](__init__.py)
- [../../scripts/mock_nano_banana.py](../../scripts/mock_nano_banana.py)
- [../../tests/test_nano_banana_client.py](../../tests/test_nano_banana_client.py)

## Why This Exists

The shared backend files already contain Nano Banana logic, but they are mixed into broader pipeline work. This workspace separates the Nano Banana-specific logic into one place so it can be reasoned about and tested independently.

## Not Changed Here

To avoid colliding with in-progress edits, this reorganization did not touch:

- `backend/agents/vision_agent.py`
- `backend/main.py`
- `backend/orchestrator.py`
- `backend/schemas.py`

Those files still reference or use Nano Banana-related behavior, but this workspace is now the clean place to consolidate that logic later.
