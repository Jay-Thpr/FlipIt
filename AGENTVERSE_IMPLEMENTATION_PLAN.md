# Agentverse + Fetch uAgents — Implementation Plan

**Purpose:** Executable plan to run all ten Fetch agents locally, register them on Agentverse (mailbox mode), keep repo docs aligned with code, and collect sponsor deliverables (ASI:One chat URL, per-agent profile URLs). Complements **`IMPLEMENTATION-PLAN.md`** Phase 6 and the profile guide **`AGENTVERSE_SETUP.md`**.

**Related docs:** [`FETCH_INTEGRATION.md`](FETCH_INTEGRATION.md), [`backend/README.md`](backend/README.md) (Fetch section), [`.env.example`](.env.example), [`API_CONTRACT.md`](API_CONTRACT.md) (`GET /fetch-agents`).

**Non-goals:** Rewriting uAgent business logic; changing `/task` or SSE contracts; owning ASI:One product behavior (discovery is best-effort).

---

## 1. Success criteria

| Outcome | Verification |
|--------|----------------|
| All 10 uAgents start under `.venv-fetch` without import errors | Ten processes (or ten successful launch logs); ports 9201–9210 not conflicting |
| Mailbox registration succeeds | Logs include successful mailbox / Agentverse registration (per agent) |
| Addresses captured | Each `agent1q...` stored in matching `*_AGENTVERSE_ADDRESS` in `.env` |
| Backend catalog accurate | `GET /fetch-agents` returns 10 rows with non-empty `agentverse_address` after env is set |
| `make check` still passes | CI / local default `FETCH_ENABLED=false` |
| Docs match repo | `AGENTVERSE_SETUP.md` prerequisites use `make run-fetch-agents`, ports 920x, correct slugs/names |
| Deliverables collected | ASI:One chat session URL + 10 Agentverse agent URLs documented for submission |

---

## 2. Canonical agent catalog (single source of truth)

Derived from [`backend/fetch_runtime.py`](backend/fetch_runtime.py) `FETCH_AGENT_SPECS` and [`.env.example`](.env.example). Use this table for Agentverse display names, CLI launch, and `.env` keys.

| Display name (uAgent `name`) | Slug (`launch` arg) | Port | Seed env var | Agentverse address env var |
|------------------------------|---------------------|------|--------------|----------------------------|
| VisionAgent | `vision_agent` | 9201 | `VISION_FETCH_AGENT_SEED` | `VISION_AGENT_AGENTVERSE_ADDRESS` |
| EbaySoldCompsAgent | `ebay_sold_comps_agent` | 9202 | `EBAY_SOLD_COMPS_FETCH_AGENT_SEED` | `EBAY_SOLD_COMPS_AGENT_AGENTVERSE_ADDRESS` |
| PricingAgent | `pricing_agent` | 9203 | `PRICING_FETCH_AGENT_SEED` | `PRICING_AGENT_AGENTVERSE_ADDRESS` |
| DepopListingAgent | `depop_listing_agent` | 9204 | `DEPOP_LISTING_FETCH_AGENT_SEED` | `DEPOP_LISTING_AGENT_AGENTVERSE_ADDRESS` |
| DepopSearchAgent | `depop_search_agent` | 9205 | `DEPOP_SEARCH_FETCH_AGENT_SEED` | `DEPOP_SEARCH_AGENT_AGENTVERSE_ADDRESS` |
| EbaySearchAgent | `ebay_search_agent` | 9206 | `EBAY_SEARCH_FETCH_AGENT_SEED` | `EBAY_SEARCH_AGENT_AGENTVERSE_ADDRESS` |
| MercariSearchAgent | `mercari_search_agent` | 9207 | `MERCARI_SEARCH_FETCH_AGENT_SEED` | `MERCARI_SEARCH_AGENT_AGENTVERSE_ADDRESS` |
| OfferUpSearchAgent | `offerup_search_agent` | 9208 | `OFFERUP_SEARCH_FETCH_AGENT_SEED` | `OFFERUP_SEARCH_AGENT_AGENTVERSE_ADDRESS` |
| RankingAgent | `ranking_agent` | 9209 | `RANKING_FETCH_AGENT_SEED` | `RANKING_AGENT_AGENTVERSE_ADDRESS` |
| NegotiationAgent | `negotiation_agent` | 9210 | `NEGOTIATION_FETCH_AGENT_SEED` | `NEGOTIATION_AGENT_AGENTVERSE_ADDRESS` |

**Naming note for judges:** Repo uses **NegotiationAgent**, not “HagglingAgent”; **EbaySoldCompsAgent**, not “EbayResearchAgent”. Update Agentverse handles/keywords accordingly.

---

## Phase A — Local Fetch runtime (blocking)

**Owner:** anyone running the stack.

1. Install main app: `make install` (`.venv`; may be Python 3.14).
2. Ensure **Python 3.12** available as `python3.12` (or set `FETCH_PYTHON` for `venv-fetch`).
3. `make venv-fetch` → creates `.venv-fetch` with `uagents` / `uagents-core`.
4. Copy [`.env.example`](.env.example) to `.env` if needed; set:
   - `AGENTVERSE_API_KEY`
   - **Ten unique** values for each `*_FETCH_AGENT_SEED` (do not reuse across agents)
   - `FETCH_USE_LOCAL_ENDPOINT=false` (mailbox)
5. **Load env in the shell** before Fetch commands (`run_fetch_agents` does not call `load_dotenv`):
   - e.g. `set -a && source .env && set +a`
6. Smoke-test **one** agent:
   - `PYTHONPATH=$PWD .venv-fetch/bin/python -m backend.fetch_agents.launch depop_search_agent`
   - Confirm no `Missing *_FETCH_AGENT_SEED` / import errors.
7. Run **all** agents: `make run-fetch-agents` (same shell with env loaded).

**Exit:** All ten processes healthy; mailbox registration messages in logs.

---

## Phase B — Agentverse registration and address capture (blocking)

**Owner:** Fetch / demo lead.

For **each** row in §2 (or in parallel once comfortable):

1. Keep that agent running (or run all via `make run-fetch-agents`).
2. Open the **Agent inspector** URL from logs (port is **9201–9210**, not 81xx).
3. Connect via **Mailbox** flow per Agentverse UI.
4. In [Agentverse](https://agentverse.ai), confirm agent appears; edit profile (name, handle, keywords, about, optional avatar) — reuse narrative from [`AGENTVERSE_SETUP.md`](AGENTVERSE_SETUP.md) but **names/slugs/ports from §2 above**.
5. Copy `agent1q...` into the matching **address env var** in `.env`.
6. Optional: start FastAPI (`make run`) and verify `GET http://localhost:8000/fetch-agents` reflects addresses.

**Exit:** All ten `*_AGENTVERSE_ADDRESS` set; profiles visible and Active where expected.

---

## Phase C — Documentation alignment (high value, low risk)

**Owner:** docs / whoever edits markdown.

1. **Edit [`AGENTVERSE_SETUP.md`](AGENTVERSE_SETUP.md)** near the top:
   - Replace prerequisites that reference `python run_agents.py`, `agents/vision_agent.py`, ports **8001/8101**, with this repo’s commands and **9201–9210**.
   - Add a pointer to §2 of **this file** for the slug ↔ env var matrix.
   - Replace “EbayResearchAgent” / “HagglingAgent” tables with **EbaySoldCompsAgent** / **NegotiationAgent** where they describe *this* codebase.
2. **Cross-link** from [`FETCH_INTEGRATION.md`](FETCH_INTEGRATION.md) “Validation checklist” to this plan’s Phase A–B.
3. **`IMPLEMENTATION-PLAN.md`** Phase 6.3: mark Agentverse steps as tracked here.

**Exit:** A new teammate can follow `AGENTVERSE_SETUP.md` + this plan without wrong ports or scripts.

---

## Phase D — Optional: published README files on the uAgent (nice-to-have)

**Owner:** backend (Fetch builder).

Today [`backend/fetch_agents/builder.py`](backend/fetch_agents/builder.py) does **not** pass `readme_path` into `Agent()`. README content in `AGENTVERSE_SETUP.md` is useful for **manual** paste into Agentverse or for future automation.

**Tasks (choose one):**

- **D1 — Docs-only:** In `AGENTVERSE_SETUP.md`, state explicitly: “Paste Overview/Features from the template into the Agentverse profile; repo does not auto-publish `agents/README_*.md`.”
- **D2 — Code:** Add optional `readme_path` per slug (e.g. under `agentverse_readmes/` or `docs/agentverse/`), wire in `build_fetch_agent`, document file naming; verify uAgents still start on 3.12.

**Exit:** Either documented manual process or working `readme_path` for at least one agent as a pattern.

---

## Phase E — Judging and ASI:One deliverables (blocking for submission)

**Owner:** demo lead.

1. Complete **≥3 interactions** per agent on Agentverse (per [`AGENTVERSE_SETUP.md`](AGENTVERSE_SETUP.md)).
2. Run ASI:One chat scenario; collect **chat session URL**.
3. Collect **10** Agentverse agent profile URLs.
4. Fill submission matrix (ASI:One URL + 10 agent URLs); store in team vault / Devpost.

**Exit:** All URLs collected; backup screenshots if live demo risky.

---

## Phase F — Optional: orchestrator via Fetch

**Owner:** integration.

Only if the demo requires FastAPI to route steps through Fetch:

1. Set `FETCH_ENABLED=true` in the environment for `make run`.
2. Run backend + Fetch agents; exercise sell/buy smoke; confirm no regression with `FETCH_ENABLED=false` in CI.

**Exit:** Documented env matrix and a short manual smoke checklist.

---

## 3. Risk register

| Risk | Mitigation |
|------|------------|
| Python 3.14 used for uAgents | Always use `.venv-fetch` / `make run-fetch-agents` |
| `.env` not loaded in shell | `set -a && source .env && set +a` before `make run-fetch-agents` |
| ASI:One does not auto-discover agents | Keywords, interactions, direct `@handle` prompts; screenshots |
| Port in use | `lsof -i :9205` (example); stop stale processes |
| Secret leak | Rotate `AGENTVERSE_API_KEY` and seeds if exposed |

---

## 4. Command cheat sheet

```bash
# One-time
make install
make venv-fetch

# Every session (Fetch)
set -a && source .env && set +a
make run-fetch-agents

# Single agent debug
PYTHONPATH=$PWD .venv-fetch/bin/python -m backend.fetch_agents.launch negotiation_agent

# E2E mailbox client → destination agent (after address known)
.venv-fetch/bin/python scripts/fetch_demo.py --address agent1q... --message "Your prompt"

# Catalog (with make run in another terminal)
curl -s http://localhost:8000/fetch-agents | python -m json.tool
```

---

## 5. Maintenance

When adding or renaming a Fetch agent:

1. Update `FETCH_AGENT_SPECS` in [`backend/fetch_runtime.py`](backend/fetch_runtime.py).
2. Update [`.env.example`](.env.example) and **§2** in this file.
3. Update `AGENT_OUTPUT_MODELS` / registry only if orchestration changes (separate from Agentverse metadata).
