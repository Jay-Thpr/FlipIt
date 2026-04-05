# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
npm start          # Start Expo dev server (interactive menu for platform selection)
npm run web        # Start for web
npm run android    # Start for Android
npm run ios        # Start for iOS
npx expo install <pkg>  # Add a dependency (use this instead of npm install for Expo compatibility)
```

No test runner or linter is configured in this project.

## Architecture

This is a **React Native / Expo** mobile app (Expo SDK 54, expo-router v6) that serves as the frontend for an autonomous resale agent system. The backend is a separate Python/FastAPI service (see `../CLAUDE.md` for backend details).

### Routing (expo-router, file-based)

- `app/_layout.tsx` — Root layout. Wraps the app in `AuthProvider` → `ThemeProvider`. Handles auth-based routing (redirects unauthenticated users to `/auth/sign-in`). Renders the `MasterAgentFAB` overlay when authenticated.
- `app/index.tsx` — Home dashboard. Shows P&L chart, horizontal carousels of sell/buy items, profile menu.
- `app/auth/sign-in.tsx`, `app/auth/sign-up.tsx` — Auth screens.
- `app/item/[id].tsx` — Item detail page (agent runs, conversations, market data).
- `app/chat/[id].tsx` — Conversation thread.
- `app/new-listing.tsx` — Create new buy/sell item.
- `app/trades.tsx` — Completed trades list.
- `app/trade/[id].tsx` — Trade detail.
- `app/settings/` — Settings screens (index, agents, notifications, platforms).

### Key Layers

**Auth & Data** — Supabase (`lib/supabase.ts`) handles auth and all database queries. `contexts/AuthContext.tsx` provides `session`, `user`, `signOut`, `accessToken` via React context. The Supabase client stores sessions in `AsyncStorage`.

**Backend Integration** — `lib/api.ts` wraps all backend HTTP calls (sell/buy pipeline runs, listing decisions, vision corrections, agent info). It auto-attaches the Supabase JWT as a Bearer token. `lib/sse.ts` provides `connectToRunStream()` for real-time SSE event consumption from agent pipeline runs.

**Theming** — `contexts/ThemeContext.tsx` + `constants/colors.ts`. Light/dark/system modes. All screens use `const { colors } = useTheme()` for dynamic styling. NativeWind (Tailwind for RN) is configured but most styling uses `StyleSheet.create`.

**Cross-screen Events** — `lib/events.ts` is a simple pub/sub emitter (`emit`/`on`) used to sync state between screens without prop drilling (e.g., `item:statusChanged`, `item:deleted`, `item:created`).

**Types** — `lib/types.ts` defines Supabase DB row types (`DbItem`, `DbConversation`, etc.). `data/mockData.ts` defines the frontend `Item` interface and display types. These two type systems coexist; DB rows are mapped to display types via `mapDbItemToItem()` in `app/index.tsx`.

### Backend API Contract

The backend runs at `EXPO_PUBLIC_API_URL` (default `http://localhost:8000`), configured in `constants/config.ts`. Key endpoints consumed:
- `POST /items/{id}/sell/run`, `POST /items/{id}/buy/run` — Start agent pipeline runs
- `GET /runs/{id}/stream` — SSE stream of pipeline events
- `GET /runs/{id}` — Poll run status
- `POST /runs/{id}/sell/correct` — Submit vision correction
- `POST /runs/{id}/sell/listing-decision` — Confirm/revise/abort listing

SSE terminal events: `pipeline_complete`, `pipeline_failed`.

### MasterAgentFAB

A floating action button (`components/MasterAgentFAB.tsx`) that opens the ASI:One chat agent. It fetches the agent address from `GET /config` on the backend and falls back to a placeholder address.

### Deep Linking

The app uses the `agentmarket` URL scheme (configured in `app.json`). The root layout handles Supabase email confirmation deep links by extracting `access_token` and `refresh_token` from URL fragments.
