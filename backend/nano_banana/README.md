# Nano Banana Workspace

This directory isolates the Nano Banana slice so it has a clear home even while shared backend files are being edited elsewhere.

## What Lives Here

- [client.py](client.py)
  - reusable async Nano Banana API client
  - env-driven settings loader
  - request payload builder
  - response URL extraction logic
- [prompts.py](prompts.py)
  - dedicated clean-photo prompt text
- [__init__.py](__init__.py)
  - convenience exports for this workspace

## Existing Shared-File Touchpoints

Nano Banana is already referenced in shared files that are currently dirty and were intentionally left untouched:

- `backend/agents/vision_agent.py`
  - current clean-photo generation flow
- `backend/config.py`
  - existing env accessors for `NANO_BANANA_API_URL` and `NANO_BANANA_API_KEY`
- `scripts/mock_nano_banana.py`
  - local mock service for Nano Banana-style responses

This workspace is meant to give your ownership area a dedicated place without conflicting with those in-flight edits.

## Current Env Contract

- `NANO_BANANA_API_URL`
- `NANO_BANANA_API_KEY`
- `IMAGE_PROCESSING_TIMEOUT_SECONDS`

## Mock Service

For local testing without the real provider:

```bash
python -m scripts.mock_nano_banana
```

Default mock endpoint:

```text
http://127.0.0.1:8010/clean
```

## Recommended Follow-Up Once Shared Files Settle

When it is safe to edit shared files again:

1. Import `NanoBananaClient` from this workspace into `backend/agents/vision_agent.py`.
2. Replace the duplicated request/response handling there with this client.
3. Keep the provider-selection logic in the shared agent, but move the Nano Banana-specific HTTP behavior here permanently.
