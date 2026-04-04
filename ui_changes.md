# UI Changes

## Homepage / First Page

1. **Remove decorative dots** — Remove the weird active green dots and purple dots.

2. **Agents in use counter** — At the top of the page, add an "agents in use" indicator showing how many agents are currently active out of the limit (limit = 10 for now). Example: "3 / 10 Agents in Use".

3. **Add agent card always accessible** — The "Add a sell/buy agent" card should not be inside the carousel. It should always be visible and easily accessible (e.g., pinned outside/below the carousel).

4. **Simplify card overlay text** — The overlay text on each agent card should only show:
   - Item name
   - Current best offer (or a placeholder like "Searching..." / "Finding..." while no offer is available)
   - Top-left corner: a text label that says either **"Active"** (green text) or **"Paused"** (gray text) — no green/red/purple lights or indicators, just styled text.

5. **Replace settings icon with profile picture** — Remove the three-line menu/hamburger icon entirely. Replace it with the user's account profile picture. Clicking the profile picture opens a dropdown or popover menu with access to all settings sections (standard account menu pattern — e.g., Settings, Account, Sign Out).

6. **Remove app subtitle** — Remove the subtitle under the app name (the "Autonomous Resale Agents" line).

## Settings Page

1. **Default appearance to system** — The default value for the appearance setting should be "System" (not light or dark).

2. **Remove green dots next to account** — Remove the green status dots that appear next to the account @ handle under the platform name.

3. **Remove wifi icon in Platforms section** — Remove the wifi/connected symbol next to the "Connected" label in the platforms section.

4. **Rename "Connected Platforms" to "Platforms"** — Drop the word "Connected" from the section title.

5. **Rename "Agent Behavior" and remove subtext** — Rename the section to "Default Agent Behavior" and remove the subtext underneath the title that reads "global default".

6. **Fix Negotiation selector layout** — The aggressive/moderate/passive dropdown is overflowing its container. Resize or restyle the selector so it fits properly within its section without looking cramped or broken.

7. **Make Usage section consistent** — Restyle the Usage section to match the visual style of the rest of the settings page (spacing, typography, card/container style, etc.).

8. **Fix back navigation label** — The back button/link that navigates to the previous page currently shows "index" — rename it to "Back".
