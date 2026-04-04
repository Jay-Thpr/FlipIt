# Fetch.ai Status

## Current State

This repo is structurally prepared for Fetch.ai integration, but it does **not** yet contain real Fetch.ai `uAgent` runtime wiring, mailbox registration, or ASI:One verification.

What is complete:

- All 10 agent services exist and run as separate FastAPI apps through [backend/run_agents.py](/Users/jt/Desktop/diamondhacks/backend/run_agents.py).
- Each agent exposes a `/chat` endpoint in [backend/agents/base.py](/Users/jt/Desktop/diamondhacks/backend/agents/base.py) so there is already a dedicated surface for future Chat Protocol behavior.
- Agent names, slugs, and fixed ports are centralized in [backend/config.py](/Users/jt/Desktop/diamondhacks/backend/config.py), which is useful for later Agentverse metadata and registration consistency.
- The backend/orchestrator contracts are stable enough that real Fetch.ai transport can be added behind the existing agent interfaces without changing frontend-facing API contracts.
- Local execution, multi-process startup, CI, and test coverage are in place, so Fetch.ai work can now be layered on top of a stable base instead of being mixed into scaffold work.

What is still placeholder-only:

- `/chat` currently returns a placeholder response, not real Fetch.ai Chat Protocol behavior.
- There is no `uagents` agent object lifecycle in the current agent files.
- There is no mailbox registration flow for any agent.
- There is no Agentverse manifest publishing.
- There is no ASI:One-discoverable deployment or verification URL yet.
- There are no per-agent Fetch.ai profile/README deliverables yet.

## Completed Repo Work Relevant To Fetch

The following backend work is already done and should be reused for Fetch integration rather than replaced:

- Stable agent process model
  The repo can launch one process per agent with fixed ports.
- Stable agent request/response contracts
  The `/task` interface is schema-validated and already used by orchestration.
- Stable orchestration layer
  SELL and BUY pipelines already sequence the 10 agents and emit SSE progress.
- Failure handling
  Timeouts, retries for transient BUY search failures, and structured failure events already exist.
- Test/build loop
  The repo already has passing tests and CI, so Fetch-specific additions can be regression-tested instead of manually validated only.

## Future Fetch.ai Tasks

These are the remaining Fetch.ai tasks to finish Jay's Fetch deliverables:

1. Add real `uagents` wiring to each agent module.
   Keep the current FastAPI `/task` app, but add the Fetch.ai agent runtime alongside it.

2. Replace the placeholder `/chat` behavior with real Chat Protocol handlers.
   Each agent should describe its role and respond with capability-appropriate text for ASI:One discovery.

3. Add environment variables for Fetch-specific secrets and seeds.
   This includes Agentverse API key, mailbox/auth configuration, and one unique seed per agent if that is the chosen setup.

4. Register all 10 agents with Agentverse mailbox support.
   Confirm logs show successful registration and that metadata is consistent across code and dashboard entries.

5. Publish Chat Protocol manifests for all agents.
   Verify each agent is visible/discoverable from Agentverse and exposes the intended capability description.

6. Create per-agent profile text/README deliverables.
   These should match the actual agent behavior and be ready to upload to Agentverse.

7. Deploy a Fetch-visible environment.
   The current backend can deploy, but Fetch verification needs a reachable environment where the uAgents are live and registered.

8. Verify ASI:One discovery end to end.
   Open an ASI:One chat, confirm it can discover the agents via Agentverse, and save the final verification URL.

9. Add Fetch-specific tests or smoke scripts.
   At minimum:
   - agent boots with Fetch runtime enabled
   - Chat Protocol handler responds
   - mailbox registration succeeds
   - manifest publishing succeeds

## Recommended Implementation Order

1. Add shared Fetch runtime support in [backend/agents/base.py](/Users/jt/Desktop/diamondhacks/backend/agents/base.py).
2. Introduce env/config support for Agentverse credentials and seeds in [backend/config.py](/Users/jt/Desktop/diamondhacks/backend/config.py) and `.env.example`.
3. Wire one agent end to end first, preferably `vision_agent`, as the reference implementation.
4. Generalize that pattern across the remaining 9 agents.
5. Validate local startup with `run_agents.py`.
6. Deploy and verify Agentverse registration.
7. Run ASI:One verification and capture the submission URL.

## Risks To Manage

- Do not break the current `/task` contract while adding Fetch runtime support.
- Do not let FastAPI and Fetch agent metadata drift apart.
- Mailbox/Agentverse propagation may take time; plan for registration delay.
- Keep Fetch integration behind feature flags or env toggles where possible so local backend testing stays simple.
- Verify one agent fully before copying the pattern across all 10.
