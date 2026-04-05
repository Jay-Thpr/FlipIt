# FlipIt — Judging Criteria Outline
**DiamondHacks 2026**

---

## Idea (1-10)
*How different is this from existing technologies? What work was done to gauge need? How many people will be impacted, and is it direct or indirect?*

### Differentiation from Existing Solutions

The SELL-side price checking space has real competitors — ThriftAI, Price Snap, ThriftFlip, and others all scan items and return profit estimates. **The key distinction: every one of them stops at information.** They tell you what something is worth, then leave you to photograph it, write a description, and fill out a listing form yourself. FlipIt closes that gap by actually drafting and populating the Depop listing via Browser Use. Research tool vs. autonomous agent.

The BUY side has no direct consumer-facing competitor. Nifty (formerly Auto Posher) automates crosslisting and sends offers to people who already liked your listings — that's seller-side automation. No product lets a buyer paste a link, have agents sweep four platforms simultaneously, rank results, and automatically send negotiated offers to sellers. eBay is only beginning to test agentic buying in partnership with OpenAI, and that's limited to their own platform.

**One-line differentiator for judges:** Existing tools are glorified price calculators that still leave all the work to the user. FlipIt is the first product to close the loop on both sides — scan to posted listing on SELL, link to negotiated offer on BUY — with no manual steps in between.

### Gauging the Need

- The market itself proves the need: eBay, Depop, and Mercari have hundreds of millions of users doing this manually today
- Competitor reviews confirm the pain: even satisfied users of ThriftAI describe it as cutting their research time "by over half" — meaning the remaining half of the workflow is still painful, and that's exactly what FlipIt addresses
- Thrift flipping is one of the fastest-growing side hustles; the behavior already exists at massive scale

### Impact

- **Direct impact:** Anyone who thrifts, flips, or hunts niche items on resale platforms — a market of hundreds of millions of active users across eBay, Depop, and Mercari alone
- **Indirect impact:** Lowers the barrier to entry for supplemental income; first-timers can now compete with experienced resellers who've built years of pricing intuition
- **Secondary angle:** Reducing friction in secondhand markets has environmental benefit — more items get resold instead of discarded

---

## Experience (1-10)
*Is the UX smooth and intuitive? Will anyone use this? Will it solve the real-world problem?*

### Smoothness and Intuitiveness

- **Camera-first design:** The SELL flow starts the moment you see an item — no typing, no search queries, just point and shoot
- **Agent activity bottom sheet:** Users watch agents fire in real time rather than staring at a blank loading screen — makes the technology feel transparent and alive
- **Persistent dashboard:** The app is useful before, during, and after each flip. It's not a one-shot tool; it's an ongoing agent management surface
- Both flows complete in under 90 seconds in demo conditions

### Will Anyone Use This?

Yes — because the target users are already doing this manually. No behavior change required. They already shop at Goodwill, already hunt resale platforms, already send offers to sellers. FlipIt fits into an existing workflow and removes the painful parts.

### Does It Solve the Real Problem?

**SELL:** The before state is 15-20 minutes of Googling, eBay tab-switching, bad photos, and manual form filling. The after state is 60 seconds from photo to "Ready to Post." That's a direct, measurable improvement.

**BUY:** The before state is checking Depop, eBay, and Mercari one by one, messaging sellers manually, usually paying asking price. The after state is pasting a link and letting agents handle everything — including the negotiation.

---

## Implementation (1-10)
*Does it function as intended? Any gaps? Can it expand? How technically impressive?*

### Functionality

- Two complete, end-to-end flows — not a demo that stops halfway
- Every API is genuinely load-bearing: Browser Use is navigating live UIs, Gemini Vision is identifying items from real photos, NegotiationAgent is sending real messages to real sellers
- Graceful fallbacks built in: eBay blocked → Mercari fires automatically; OfferUp blocked → "unavailable" badge, demo continues without crashing

### Technical Impressiveness

**1. Dual-path architecture**
ASI:One handles multi-agent orchestration and discoverability on Agentverse. FastAPI mirrors the exact same pipeline for low-latency mobile execution. One agent system, two front doors — the Fetch.ai narrative stays intact while the mobile demo remains fast and reliable.

**2. Browser Use inside agent logic**
The agents are not hitting unofficial APIs or parsing static HTML. They are navigating live web UIs — filling forms, clicking through pagination, sending messages — exactly as a human would. Significantly harder and more robust than traditional scraping.

**3. Genuine multi-agent system**
10 registered Fetch.ai agents, Chat Protocol on all of them, discoverable by ASI:One. This is not a single model with tool calls dressed up as agents. Each agent has a distinct role, runs independently on Render, and coordinates through a real orchestration layer. Make this distinction explicit to judges — it directly hits the "multi-agent collaboration" criterion.

**Additional technical highlights:**
- Gemini Vision for in-store item identification
- Semantic ranking across four platforms simultaneously
- Generative negotiation messages unique per seller to avoid spam detection

### Expandability

The agent architecture makes expansion straightforward — adding a new platform means writing one new SearchAgent and dropping it into the roster. The orchestration layer handles the rest. The VisionAgent and pricing pipeline are category-agnostic, meaning the same system works for electronics, furniture, and books without rebuilding anything.

**Expansion vectors:**
- New platforms: Poshmark, Vinted, Facebook Marketplace — one agent each
- New verticals: electronics, furniture, books — same pipeline
- New capabilities: price history, push notifications for offer replies, batch scanning

---

## Demo (1-10)
*Clarity and presentation of the 2-minute pitch.*

### Structure (Two 60-Second Arcs)

**Open with the problem, not the product.**
"Everyone here has either been to a thrift store and wondered if something was worth buying, or spent way too long hunting for something specific and ended up paying full asking price anyway."

**Arc 1 — SELL (60 seconds)**
1. "You just found this at Goodwill. Is it worth buying?"
2. Open app → tap "+" → take photo
3. VisionAgent fires — item identified, clean photo appears
4. EbayResearchAgent — comp table populates: "Real sold prices from eBay."
5. PricingAgent — profit margin appears: "After fees, you make $Y."
6. DepopListingAgent — form populated, item card appears: "Ready to post."
7. "That took 60 seconds. It used to take 20 minutes."

**Arc 2 — BUY (60 seconds)**
1. "You want these specific Jordan 1s. You refuse to pay asking price."
2. Paste product link → submit
3. Search agents fire sequentially — platform badges animate: "Checking every resale platform."
4. RankingAgent — ranked listings appear: "31 listings. These 5 are below market."
5. NegotiationAgent fires — offer tracker shows "Sent" badges
6. **The closer:** "We sent offers to real sellers before this presentation. One already replied." → show the reply

### Key Presentation Tips

- **Get to the camera fast** — don't over-explain before showing the demo. Judges are watching many projects; the one that shows something real happening on screen first wins attention
- **Say the numbers out loud:** "Twenty minutes versus sixty seconds" is a punchline that sticks
- **The seller reply is your close** — treat it like a reveal, not a footnote. A real reply from a real account converts the demo from impressive-tech to this-is-a-real-product
- **Own the timeline:** "We built 10 running agents in 24 hours" reframes the evaluation from "is this polished" to "is this remarkable given the constraints" — on that axis you are very strong
- **The raccoon mascot and FlipIt branding signal product thinking** — have the logo visible. It tells judges this team thought about a real product, not just a hackathon submission
