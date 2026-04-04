# DiamondHacks 2026 Brainstorm — Full Chat Context

Paste this into a new Claude chat to continue where we left off.

---

## Who I Am

- Name: Jay, CS student at UCLA
- Strong technical background (full-stack, comfortable with most stacks)
- Looking for teammates — currently have one backend/fullstack teammate, aiming for team of 4 (or duo)
- Competing at **DiamondHacks 2026** at UCSD, April 5-6 2026 (this weekend)

---

## What I Want in a Project

- **"Wait, you built WHAT?" energy** — audacious, surprising, makes judges lean in. Not just useful, but jaw-dropping. Like a friend who built a Fetch.ai agent that calls hotels via TTS and actually books the cheapest room — end-to-end autonomous execution of a task people didn't think was automatable.
- **Visually impressive** — the output or demo itself should be visually stunning. Not a headless browser clicking around.
- **Great tech stack** — something I can talk about in interviews. Resume-worthy.
- **Standalone product** — feels like a real product, not a hackathon toy.
- **Niche** — not overdone. If I describe it and a judge says "we've seen three of these today," it's disqualified.
- **Multi-track stacking** — ideally wins an overall prize + a sponsor track prize + a main track prize + side tracks (AI/ML, UI/UX).

---

## Tracks I've Ruled Out

- **Qualcomm Multiverse** — didn't register in time
- **Interactive AI (UCSD CSE)** — dropped it. Entertainment constraint fights against building something technically serious. Limited resume value. Doesn't stack well with other tracks since focus is entertainment not utility.
- **AI personal trainer / exercise form analyzer** — overdone, judges have seen it a hundred times

---

## Tracks Still on the Table (Ranked by Prize Value)

### Sponsor Tracks
1. **Browser Use** — Biggest prizes (2x iPhone 17 Pro, 2x AirPods Max, SF hacker house trip). Open-source Python lib that gives AI agents real hands to control a browser — clicks, forms, navigation, multi-tab. Not just scraping. Agents that *do things* on websites. Judged on "how well does it deliver for its intended audience."
2. **TwelveLabs** — Video understanding API. Marengo = embedding model for semantic video search ("find the moment where X happens"). Pegasus = generative model that watches video and outputs text summaries, Q&A, highlights. Prizes are credits (~$270 value), but it makes demos visually impressive and is strong for resume.
3. **Fetch.ai** — $300/$200 cash. Build agents on Agentverse (2M+ agent directory), demonstrate through ASI:One (their consumer AI that orchestrates agents). Use any framework (Claude SDK, LangGraph, etc.). Must implement Chat Protocol. Pairs naturally with Browser Use.
4. **Jelly API (JellyJelly)** — $500 stablecoins + summer fellowship. Social network on Solana (founded by Venmo co-founder). Video chats/livestreams → shareable monetizable clips ("Jellies"). JELLYJELLY token for tipping, boosting, paywalling. Haven't researched this fully yet.
5. **Best Use of Gemini** — Google swag. Gemini 3 API — multimodal, reasoning, function calling, Google Search grounding, image gen (Imagen 4), TTS. Easy to layer onto almost any project.
6. **Best Use of ElevenLabs** — Wireless earbuds. Best-in-class TTS API — 32 languages, emotionally expressive, instant voice cloning from 60s of audio, 10k+ voices, also does STT, sound effects, music gen, dubbing.
7. **Best Use of Solana** — Ledger Nano S Plus. High-perf blockchain, near-zero fees, thousands of TPS. Smart contracts in Rust/Anchor.
8. **Best Use of Vultr** — Portable screens. Cloud infrastructure (like simpler AWS) with on-demand NVIDIA H100/GH200/A100 GPUs, serverless inference, managed Kubernetes. Free credits at hackathon. Use as infrastructure backend regardless of whether targeting this prize.
9. **Best .Tech Domain** — Desktop mic + 10-year domain. Basically free. Register a domain for the project no matter what.

### Main Tracks (pick one)
- **Alchemy of the Earth** — Sustainability/social impact. Owala 40oz bundle.
- **Elixirs of Vitality** — Health. Peak Design Tech Pouch.
- **The Scholar's Spellbook** — Education. Mini Projector.
- **Enchanted Commerce** — Commerce/e-commerce. Apple AirTags.
- **The Rogue's Ritual** — Wildcard. Sony speaker.

Jay leans toward Alchemy of the Earth or Scholar's Spellbook (likes the energy of those) but is open to any.

### Side Tracks (stackable on top of everything)
- Best AI/ML Hack — JBL Go 3 (almost any project qualifies)
- Best UI/UX Hack — Philips Hue 2-pack (invest in polish)
- Best Mobile Hack — Massage gun (React Native wrapper if time allows)
- Best Duo Hack — 27" monitor (if team ends up as 2 people)

---

## Key Strategic Insights

- **Browser Use has disproportionately high prizes** — designing around it is high expected value, but competition will be high too. Need a niche enough angle to stand out.
- **The winning project should feel end-to-end autonomous** — it doesn't recommend, it *does*. The hotel booking example (Fetch.ai agent that calls hotels via TTS to book the cheapest room) is the north star for this energy.
- **Niche angle + clean demo > broad idea + clunky demo** — judges remember demos that surprise them.
- **Visual output matters** — Jay wants something visually impressive. Headless automation without visual payoff doesn't fit.
- **Tech stack should read well on a resume** — "I built an interactive entertainment app" is weak. "I built an autonomous agent pipeline that does X with TwelveLabs + Browser Use + Fetch.ai" is strong.
- **Free add-ons**: claim Vultr credits, register .Tech domain — free extra prizes on any project.

---

## Ideas Explored So Far

### Strong Contenders
1. **Greenwashing Detector / Sustainability Auditor** (Browser Use + Fetch.ai + Alchemy of the Earth)
   - Agents swarm across corporate websites, ESG reports, EPA filings, news — cross-reference sustainability claims against real data — output a credibility score with receipts
   - Demo: type in "Shell" or "Amazon", watch agents work live, get a breakdown
   - Niche: nobody builds accountability tools at hackathons. Everyone builds tools that help users, not tools that hold institutions accountable.
   - Strong Browser Use case (agents navigate complex web UIs, not just APIs)
   - Adds Fetch.ai naturally as orchestration layer
   - Clean Alchemy of the Earth fit
   - Downside: not as visually "wow" as Jay wants

2. **Video-to-3D Pipeline** (TwelveLabs + NVIDIA Komodo + Education or Wildcard)
   - Feed video in → TwelveLabs understands what's in it semantically → Komodo generates 3D models from key frames → navigable 3D scene in browser (Three.js / React Three Fiber)
   - Use cases: virtual museum from phone footage, 3D science models from lecture video, historical site preservation
   - Demo is visually stunning — rotate a 3D model generated from video in real-time
   - Tech stack reads incredibly well: TwelveLabs API + 3D reconstruction pipeline + WebGL viewer + Next.js
   - Niche: nobody has a pipeline like this at the hackathon
   - Downside: technically risky under hackathon time pressure. 3D reconstruction pipelines can be finicky.

### Ideas Ruled Out
- AI personal trainer / exercise form coach — overdone, zero niche factor
- Bill negotiator agent — clever but headless, not visual
- Job application auto-filler — clever but not visual

---

## Where We Left Off

We dropped Interactive AI from consideration. The last question on the table was: **what's the project that hits "wait you built WHAT?" + visually impressive + great tech stack + resume-worthy?**

The two strongest remaining candidates are the greenwashing detector (Browser Use-anchor, high prize value, niche) and the video-to-3D pipeline (visually stunning, strong tech stack, technically risky).

Neither has been committed to. Still exploring. Next step: keep brainstorming with this context, potentially exploring other directions entirely that haven't been considered yet.

---

## Files Created (on Jay's Desktop in /diamondhacks folder)
- `tracks.md` — full track descriptions with company/product explainers
- `brainstorm-permutations.md` — exhaustive permutation map of all track intersections, sponsor cross-pollinations, three/four-way combos, niche ideas, and prize stacking strategy
