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

## Listing Detail Page (per listing popup)

1. **Remove box around back arrow** — The back arrow should not have a box/container around it. Just show the bare arrow.

2. **Make Overview and Settings consistent with main settings page** — The per-listing overview and settings areas look inconsistent with the account/settings page. Restyle them to match the same visual language (spacing, typography, card style, etc.).

3. **Remove repeated item name from Overview** — The item name already appears at the top of the page, so don't repeat it inside the overview section.

4. **Default settings to account-level defaults** — All per-listing settings that are meant to override account defaults should be pre-filled with the values from account settings. They are overrides, not standalone configs.

5. **Remove "Auto Relist" setting** — This setting is unnecessary. If an agent is active it should continuously attempt to sell/buy the item without needing a relist toggle.

6. **Add AI active/paused toggle** — Add a switch to activate or stop the AI agent for this listing.

7. **Add archive listing option** — Add a way to archive a listing, with a confirmation dialog before it takes effect.

8. **Simplify Market Overview cards** — Each market overview should only display:
   - Best buy price
   - Best sell price (the spread)
   - Number of listings
   - Market name — use the actual company name (e.g., "eBay", "Facebook") or the official company logo. No custom widgets or abstract icons.

9. **Unread conversation indicator** — Remove the purple dot for unread messages in the Active Conversations list. Instead, make the preview text **white** when unread and **grayed out** (current style) when already read.

10. **Add "Best Current Offer" to Overview** — Include a best current offer field in the overview section.

## Active Conversation Page (inside a conversation)

1. **Consistent back arrow** — Style the back arrow the same way as everywhere else in the app (no box, bare arrow).

2. **Replace platform widget with company logo or name** — Remove the little widget showing where the conversation is from. Replace it with the official company logo or company name (consistent with the rest of the app). The logo should fill the space on the right side of the top bar.

3. **Remove the subbar under the contact name** — Delete the secondary bar beneath the user you're talking to (the one that shows "Log view only — all messages sent by your agent").
