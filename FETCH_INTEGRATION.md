# Fetch Integration Overview

## Purpose

This document explains the current Fetch.ai integration in the repo, what has already been implemented, what has been verified, and what still needs to be done to make the Fetch agents production-ready and fully aligned with Browser Use.

The project is mobile-first. The mobile app remains the main product surface. Fetch.ai exists as a parallel agent-discovery and judging path, not as the primary app runtime.

## Current Architecture

There are now two parallel execution layers in the backend:

1. Product path
   - Mobile app calls FastAPI.
   - FastAPI orchestrates `sell` and `buy` pipelines.
   - Individual backend agents run local logic and, where available, Browser Use tasks.
   - SSE streams progress back to the mobile app.

2. Fetch path
   - Fetch `uAgents` expose the same capabilities to Agentverse and ASI:One.
   - The Fetch agents do not reimplement the business logic.
   - They call back into the existing backend agent logic through a shared runtime bridge.

This keeps the mobile backend and the Fetch demo path aligned.

## Files Added For Fetch

- [backend/fetch_runtime.py](/Users/eliotboda/Desktop/Projects/DiamondHacks/backend/fetch_runtime.py)
  - Shared bridge from chat requests into the existing backend agent chain.
- [backend/fetch_agents/builder.py](/Users/eliotboda/Desktop/Projects/DiamondHacks/backend/fetch_agents/builder.py)
  - Builds ASI:One-compatible `uAgents` using `chat_protocol_spec`.
- [backend/fetch_agents/launch.py](/Users/eliotboda/Desktop/Projects/DiamondHacks/backend/fetch_agents/launch.py)
  - Launches one Fetch agent by slug.
- [backend/run_fetch_agents.py](/Users/eliotboda/Desktop/Projects/DiamondHacks/backend/run_fetch_agents.py)
  - Launches all Fetch agents as subprocesses.
- [tests/test_fetch_runtime.py](/Users/eliotboda/Desktop/Projects/DiamondHacks/tests/test_fetch_runtime.py)
  - Verifies the Fetch runtime bridge and chat-to-agent mapping.

## Existing Backend Files Updated

- [requirements.txt](/Users/eliotboda/Desktop/Projects/DiamondHacks/requirements.txt)
  - Added `uagents==0.24.0` and `uagents-core`.
- [.env.example](/Users/eliotboda/Desktop/Projects/DiamondHacks/.env.example)
  - Added Fetch/Agentverse env vars and agent seed vars.
- [Makefile](/Users/eliotboda/Desktop/Projects/DiamondHacks/Makefile)
  - Added `run-fetch-agents`.
- [backend/README.md](/Users/eliotboda/Desktop/Projects/DiamondHacks/backend/README.md)
  - Added setup notes for Fetch and how it fits with Browser Use.
- [.gitignore](/Users/eliotboda/Desktop/Projects/DiamondHacks/.gitignore)
  - Expanded to ignore local venvs and runtime clutter.

## What Is Implemented Now

### 1. Fetch agent scaffolding

Each agent slug now has a Fetch-side spec with:

- name
- port
- seed env var
- short capability description

These specs live in [backend/fetch_runtime.py](/Users/eliotboda/Desktop/Projects/DiamondHacks/backend/fetch_runtime.py).

### 2. ASI:One-compatible chat protocol wiring

The Fetch builder uses:

- `Agent(...)`
- `mailbox=True`
- `publish_agent_details=True`
- `Protocol(spec=chat_protocol_spec)`
- `ChatAcknowledgement`
- `ChatMessage`
- `TextContent`
- `EndSessionContent`

This follows the official ASI:One-compatible pattern.

### 3. Shared runtime bridge

The Fetch agents do not contain duplicate marketplace logic.

Instead:

- sell-side Fetch requests route into the existing SELL chain
  - `vision_agent`
  - `ebay_sold_comps_agent`
  - `pricing_agent`
  - `depop_listing_agent`

- buy-side Fetch requests route into the existing BUY chain
  - `depop_search_agent`
  - `ebay_search_agent`
  - `mercari_search_agent`
  - `offerup_search_agent`
  - `ranking_agent`
  - `negotiation_agent`

This means the same agent logic is shared between:

- mobile app backend execution
- local FastAPI agent apps
- Fetch/ASI:One agent exposure

### 4. Browser Use alignment

Some backend agents already attempt Browser Use first and fall back to deterministic logic when Browser Use is unavailable.

That currently applies to:

- marketplace search agents
- eBay sold comps research
- listing/negotiation paths where Browser Use support exists

So the Fetch path already benefits from Browser Use indirectly because the Fetch bridge reuses those same backend agents.

## What Has Been Verified

### Repo-level verification

Passed:

- `tests/test_fetch_runtime.py`
- `tests/test_http_execution_and_launcher.py`
- `tests/test_agents.py`

This verifies:

- Fetch chat requests can be mapped into existing backend agent flows
- existing backend agent contracts still work
- the new Fetch bridge does not break the current backend scaffold

### Runtime verification

Verified:

- The Fetch code does not run correctly on Python `3.14`
- The Fetch code does run correctly on Python `3.12`
- A real Fetch agent object can be created on Python `3.12`
- A real `uAgent` process can start and expose a stable agent address
- Manifest publication succeeds
- Almanac API registration succeeds

Observed blocker:

- Mailbox creation is not yet completed for the running local agent

## Important Environment Note

The Fetch `uAgents` runtime used here is not compatible with the local Python `3.14` environment that was originally active in this repo.

Use a Python `3.12` or `3.13` virtual environment for the Fetch agents.

Current working Fetch env pattern:

```bash
python3.12 -m venv .venv-fetch
source .venv-fetch/bin/activate
pip install -r requirements.txt
```

## How Fetch And Browser Use Work Together

They serve different roles.

### Browser Use

Browser Use is the execution layer for real marketplace work:

- searching listings
- extracting sold comps
- preparing listing forms
- sending offers/messages

### Fetch.ai

Fetch is the discovery and sponsor-demo layer:

- agent registration on Agentverse
- discoverability via ASI:One
- standardized chat interface to agent capabilities

### Combined model

The right model is:

- Browser Use does the real browser work
- Fetch exposes the capability to ASI:One

That is why the Fetch path should keep calling the same backend agent logic instead of forking into a separate implementation.

## What Still Needs To Be Done

### 1. Finish mailbox setup

The first live agent starts, but mailbox creation/attachment is not yet complete.

This is the current immediate blocker for a full Agentverse test.

### 2. Improve chat input parsing

Right now chat input is mapped into backend agent requests with lightweight parsing:

- URL extraction
- budget extraction
- plain-text query mapping

Future work:

- better sell-side parsing for images, item descriptors, and conditions
- richer buy-side parsing for platform preferences and negotiation intent

### 3. Make agent metadata stronger

Future improvements:

- better agent descriptions
- explicit Agentverse profile metadata
- per-agent README content for judging
- tags and capability descriptions aligned to the hackathon story

### 4. Add Browser Use coverage to more agents

Some Browser Use hooks already exist, but the repo still mixes:

- live Browser Use paths
- deterministic fallback paths

Future work:

- complete Browser Use support for all marketplace-facing agents
- ensure output contracts stay stable when switching from fallback to live browser execution
- add more explicit Browser Use event reporting for frontend/mobile visibility

### 5. Add a stronger Fetch-to-Browser Use contract

Right now the Fetch path reuses backend logic successfully, but this contract can be improved by:

- surfacing Browser Use-specific execution status in Fetch responses
- clarifying whether a result came from live browser execution or fallback logic
- optionally exposing confidence / execution-mode fields in agent outputs

### 6. End-to-end ASI:One validation

Still needed:

- mailbox registration success
- Agentverse discoverability check
- ASI:One prompt/response validation
- shared chat URL or demo proof for submission

### 7. Deployment readiness

Still needed if these agents move beyond local demo:

- externally reachable endpoints
- seeded and documented environment configuration
- deploy strategy for running all Fetch agents alongside the backend
- persistent Browser Use profile strategy where login state matters

## Next Steps To Get Fetch And Browser Use Fully Running

This is the recommended order to get from the current scaffold to a working end-to-end setup.

### Step 1: Keep the product path stable

Do not make ASI:One the main runtime for the mobile app.

The stable path should remain:

- mobile app
- FastAPI backend
- backend agents
- Browser Use where needed

Fetch should remain a parallel agent exposure layer.

### Step 2: Make Browser Use reliable on the backend first

Before scaling Fetch to all agents, validate the browser-backed agents locally from the backend side.

Priority order:

1. `depop_search_agent`
2. `ebay_search_agent`
3. `ebay_sold_comps_agent`
4. `depop_listing_agent`
5. `negotiation_agent`

For each of those:

- create the necessary logged-in browser profile under `profiles/`
- confirm the corresponding backend agent uses Browser Use instead of fallback logic
- confirm the output still matches the existing schema

The Browser Use and fallback outputs must stay contract-compatible so the orchestrator and Fetch bridge can treat them the same way.

### Step 3: Finish one real Fetch agent end to end

Do not try to finish all 10 Fetch agents first.

Start with:

- `depop_search_agent`

Why:

- simple input shape
- clear result set
- already aligned with Browser Use search behavior
- low risk compared with multi-step sell or negotiation flows

Done means:

- agent runs under Python 3.12/3.13
- mailbox is created successfully
- Agentverse recognizes the agent
- ASI:One can send a prompt and receive a usable response

### Step 4: Connect Fetch responses more explicitly to Browser Use execution

Right now the Fetch bridge reuses the backend agent logic, which is correct, but the chat response does not clearly say whether the result came from:

- live Browser Use
- deterministic fallback

Future improvement:

- add an execution-mode field to the agent outputs
- include whether Browser Use actually ran
- include fallback reason if Browser Use was unavailable

That will make judging and debugging much easier.

### Step 5: Strengthen error handling for live platform gaps

When Browser Use is live, empty marketplace results are normal.

The repo now protects the ranking path from crashing on an empty candidate set, but more work is still useful:

- emit a clear no-results summary for search agents
- allow ranking/negotiation to short-circuit gracefully
- return a user-friendly response through Fetch when no listings were found

This matters because the live Browser Use path is less predictable than deterministic fallback data.

### Step 6: Decide how Fetch should call the backend logic long term

Current implementation:

- Fetch agents call the local backend agent registry directly

That is fine for now because it keeps behavior aligned.

Long-term options:

1. Keep the current direct-call model
   - simplest
   - lowest duplication
   - good for hackathon speed

2. Route Fetch agents through authenticated internal FastAPI endpoints
   - closer to the product runtime
   - better observability
   - more moving parts

For the hackathon, the current direct-call bridge is the right tradeoff.

### Step 7: Expand to more Fetch agents only after one path is stable

Recommended rollout:

1. `depop_search_agent`
2. `ebay_search_agent`
3. `ranking_agent`
4. `vision_agent`
5. `pricing_agent`
6. remaining agents

That sequence gives you:

- one simple search demo
- multi-search aggregation
- ranking story
- sell-side story
- full multi-agent story

### Step 8: Prepare the submission deliverables

Still needed for the final sponsor story:

- Agentverse URLs for the registered agents
- ASI:One chat proof
- per-agent README/profile copy
- a short explanation of how Browser Use powers real actions while Fetch provides discoverability

The final narrative should be:

- the mobile app is the product
- FastAPI is the product orchestration layer
- Browser Use is the real marketplace execution layer
- Fetch/Agentverse/ASI:One expose the same agents to the sponsor ecosystem

## Recommended Next Steps

1. Finish mailbox setup for one agent, ideally `depop_search_agent`.
2. Verify that one agent is discoverable and usable from ASI:One.
3. Add per-agent README/profile content for judging.
4. Expand Browser Use-backed live execution on the most important marketplace agents.
5. Only after one agent is fully working, scale the Fetch registration flow to the remaining agents.

## Recommended First Production-Ready Agent

Best first candidate:

- `depop_search_agent`

Why:

- simple user input shape
- direct Browser Use utility
- easy to explain in ASI:One
- low dependency chain compared with multi-step sell-side agents

Second best candidate:

- `ranking_agent`

Why:

- stronger multi-agent story for the Fetch sponsor demo
- better demonstration of coordination once the search agents are stable
