# Domain Pitfalls: Dispensary Deal Aggregation Dashboard

**Domain:** Cannabis dispensary menu/deal scraping and aggregation
**Researched:** 2026-04-10
**Confidence:** HIGH for scraping/SMS pitfalls (multiple verified sources); MEDIUM for FL-specific regulatory context

---

## Critical Pitfalls

Mistakes that cause rewrites, silent data corruption, or project-stopping blockers.

---

### Pitfall 1: Assuming Twilio (or any mainstream SMS provider) Will Work for Cannabis Content

**What goes wrong:** You build the SMS alert feature on Twilio, test it with benign content, and it works. Then you send a message mentioning a deal at a dispensary and the message is silently filtered or your account is terminated. Twilio explicitly prohibits cannabis-related messaging "regardless of federal or state legality." AT&T and T-Mobile enforce the same ban at the carrier level.

**Why it happens:** Developers assume state legality = permissible carrier use. It doesn't. The restriction is federal-legality-based and carrier-enforced — not just a Twilio policy. Even indirect references (linking to a cannabis site, mentioning a dispensary name) can trigger filtering.

**Consequences:**
- Silent message drops with no error — you think SMS is working, Jared never gets alerts
- Account suspension mid-project
- Full SMS feature rewrite if wrong provider is baked in

**Warning signs:**
- Using Twilio, AT&T, T-Mobile, Vonage, Bandwidth, or other mainstream telecom-backed providers
- No cannabis-specific provider research done before implementation
- SMS working in test (test content doesn't mention cannabis)

**Prevention:**
- Select a cannabis-compliant SMS provider from the start. SpringBig and AlpineIQ are purpose-built for cannabis; however, they target dispensary businesses, not individual consumers
- For a single-user personal tool, the most reliable path is app-based push notifications (Pushover, ntfy.sh, or similar) which have zero carrier restrictions and zero content filtering
- If SMS is hard-required, use a compliant provider and avoid explicit dispensary/product names in the message body — link to the dashboard instead
- Decide the delivery mechanism in Phase 1 before writing a single line of alert code

**Phase:** Must be resolved before any SMS/alert implementation phase.

---

### Pitfall 2: Building Scrapers Against Direct Dispensary Sites Without API Research First

**What goes wrong:** You build scrapers for Trulieve.com, Curaleaf.com, Surterra.com, etc. directly. These are React/Next.js SPAs with JavaScript-rendered menus. Within weeks, one site deploys a redesign or enables Cloudflare bot protection. The scraper silently starts returning empty data or wrong prices — not an error, just wrong output.

**Why it happens:** Florida's major chains (Trulieve, Curaleaf, Surterra/Parallel, AYR, Cookies, Sunnyside, Fluent, MUV) all use modern JavaScript-heavy frontends. Their menus are rendered client-side, meaning raw HTTP requests return no product data. And many are served behind Cloudflare, which actively fingerprints and blocks automated headless browsers.

**Consequences:**
- Headless browser dependency (Playwright/Selenium) adds 300-500MB to the stack and significant latency per scrape
- Cloudflare detection causes intermittent failures that look like network errors
- A single site redesign can break a scraper silently — the scraper runs successfully but collects empty or malformed data

**Warning signs:**
- Scraper targets `<div class="product-card">` or similarly generic CSS class names
- No schema validation on scraped data (price/name fields not checked for expected format)
- No alerting when a scraper returns 0 results

**Prevention:**
- First check whether the dispensary powers its menu through Dutchie or Jane (embedded iframe or API call visible in browser DevTools Network tab) — Dutchie embeds have a more stable structure than custom sites
- Use semantic/structural selectors (`data-testid`, `aria-label`, schema.org markup) over positional CSS selectors
- Build a validation layer: if a scrape run returns 0 products or prices outside a reasonable range, treat it as a scraper failure, not a data result
- Add per-source health monitoring from day one, not as a v2 feature

**Phase:** Scraper architecture and source selection must happen before implementation. Add health checks in the same phase as the scrapers, not after.

---

### Pitfall 3: Treating Aggregator APIs (Weedmaps, Leafly) as Self-Service Public APIs

**What goes wrong:** Research shows Weedmaps and Leafly have public-facing developer portals, so you plan to use their APIs as the primary data source. Both require formal partner/integrator agreements — they are not public, self-service APIs.

**Why it happens:** The developer documentation is publicly viewable, which implies open access. It doesn't. Both Weedmaps and Leafly require you to email a partnerships team, describe your business use case, and sign agreements. These approvals are for POS integration partners and dispensary technology vendors — not individual consumer tools.

**Consequences:**
- Weeks of waiting for approval that may never come for a personal project
- Project blocked at the data layer before a single line of scraping code is written
- If approval is granted, ToS may prohibit storing or redistributing menu data

**Warning signs:**
- Project plan lists "Weedmaps API" or "Leafly API" as a primary data source
- No investigation of Dutchie's embedded public menus as an alternative
- No fallback scraping strategy documented

**Prevention:**
- Treat aggregator APIs as unavailable unless explicitly confirmed — design the data layer around scraping from the start
- Dutchie-powered menus are the most accessible alternative: many FL dispensaries embed Dutchie menus, and their menu pages have a more consistent structure than bespoke sites. Apify has published working scrapers against Dutchie as of 2025, confirming the structure is accessible
- Weedmaps does have public-facing listing pages (not API) that can be scraped — verify their robots.txt and ToS before relying on this

**Phase:** Data sourcing strategy must be finalized in the very first research/planning phase.

---

### Pitfall 4: Silent Scraper Failures Poisoning the Dashboard with Stale Data

**What goes wrong:** A scraper fails mid-run (rate limited, site down, structure changed). The previous day's data stays in the database. The dashboard shows deals that expired yesterday — or worse, deals that no longer exist. Jared drives to a dispensary for a deal that ended.

**Why it happens:** Scrapers are run on a schedule. If the run fails silently (exception caught and logged but not surfaced), the last successful run's data persists as "current." This is the most common production failure mode for scraping pipelines. It is especially dangerous for deal data, which is inherently time-bound and changes daily.

**Consequences:**
- Incorrect purchasing decisions — the entire value prop of the tool is destroyed
- Trust erosion: Jared checks the dashboard, drives out, deal isn't there

**Warning signs:**
- No last-scraped timestamp visible on the dashboard
- Scheduler (cron) has no notification on failure
- Database records have no TTL or freshness timestamp

**Prevention:**
- Store a `last_scraped_at` timestamp per dispensary source and display it prominently on the dashboard
- Mark deals as "potentially stale" if `last_scraped_at` is older than 26 hours (catches a missed daily run)
- Treat 0-result scrape runs as failures, not empty inventories — no dispensary has zero products
- Build failure alerting (even just a log file that the dashboard reads) before the first production scrape

**Phase:** Must be built alongside the first scraper, not added later.

---

## Moderate Pitfalls

---

### Pitfall 5: Geofencing by Zip Code Produces Wrong Results

**What goes wrong:** You filter dispensaries by "within 20 miles of 34982" using zip code centroid distance. But 34982 is in Fort Pierce, and the 20-mile radius catches dispensaries in Port St. Lucie, Stuart, and Okeechobee. The zip centroid approach miscalculates distances for dispensaries near the boundary, and dispensary address data from scraped sources often has inconsistent formats (some have lat/long, most have street addresses only).

**Prevention:**
- Geocode dispensary addresses to lat/lng at scrape time using a geocoding API (Google Maps Geocoding API or Nominatim/OSM for free)
- Calculate great-circle distance from the 34982 centroid (27.4170° N, 80.3498° W) to each dispensary's geocoded coordinates
- Cache geocoded coordinates — these don't change; don't re-geocode every run
- The 34982 zip covers Fort Pierce proper; verify the 29 dispensaries reported by Weedmaps for the PSL/Fort Pierce metro are correctly bounded

**Phase:** Dispensary list and distance filtering in the foundational data phase.

---

### Pitfall 6: CSS Selector Fragility Without a Maintenance Strategy

**What goes wrong:** Scrapers use specific CSS class names that change when a dispensary updates their site. Since Florida's major chains (Trulieve has 160+ locations nationally) run frequent A/B tests and rolling deployments, selectors can break without a full redesign.

**Prevention:**
- Prefer `data-testid`, `aria-*`, or schema.org structured data attributes over auto-generated class names (e.g., `class="sc-abc123"` is a styled-components hash — it will change)
- Where possible, target HTML semantics: `<h2>` for product name, `<span>` near dollar signs for price
- Modularize scrapers: one file per dispensary source. When one breaks, others keep running
- Automated regression test: after each scheduled scrape, check that at least N products were collected per source

**Phase:** Scraper implementation phase.

---

### Pitfall 7: Florida Medical-Only Regulatory Context Affects Data Interpretation

**What goes wrong:** You display deals without context that this is a medical-only market. Florida's Amendment 3 (recreational legalization) failed in November 2024. All purchases require a valid medical marijuana card. Deal quality comparisons that reference "recreational pricing" from other states are irrelevant. Additionally, Florida restricts certain marketing practices for dispensaries, which can mean that some "deals" displayed on websites are restricted promotions that require card verification to redeem.

**Prevention:**
- Do not surface recreational-market pricing benchmarks as comparison data
- Note in the UI that all dispensaries require a valid FL medical card
- Be aware that some scraping of "deal" pages may require session cookies or a logged-in state if the dispensary gates deal visibility behind medical card verification — test each source for this explicitly

**Phase:** UI/display phase and source research phase.

---

### Pitfall 8: Deal Deduplication Across Multiple Sources

**What goes wrong:** The same dispensary is listed on Weedmaps, has a Dutchie-powered menu, and has its own website. Scraping all three for completeness means the same deal appears 2-3 times in the dashboard, making it harder to use.

**Prevention:**
- Define a canonical dispensary identifier (e.g., normalized chain name + address) early
- During ingest, deduplicate by dispensary ID + product name + price — not just product name
- If scraping multiple sources for the same dispensary, pick one authoritative source per dispensary rather than merging from all

**Phase:** Data model design, before first scraper ships.

---

## Minor Pitfalls

---

### Pitfall 9: Rate Limiting Without Backoff

**What goes wrong:** The daily refresh scrapes all dispensaries sequentially at full speed. Sites with rate limits (or Cloudflare) start blocking after N requests in M seconds.

**Prevention:**
- Add a random delay (1-3 seconds) between page requests per source
- Rotate user-agent strings
- Schedule scrapers with per-source staggered start times, not all at once

---

### Pitfall 10: Storing Full HTML Instead of Structured Data

**What goes wrong:** To avoid breaking on site changes, scrapers dump raw HTML to disk. Storage grows unbounded, and querying "what deals are available today" requires re-parsing all HTML on every dashboard load.

**Prevention:**
- Parse and extract structured data (dispensary, product, category, price, discount, scraped_at) at scrape time
- Store structured records in SQLite — not raw HTML
- Keep raw HTML only if you need to debug parser failures, and purge after 48 hours

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| SMS/alert provider selection | Twilio ban on cannabis content (silent failures) | Decide delivery mechanism before writing alert code; consider app-based push (Pushover/ntfy) over SMS |
| Data source selection | Weedmaps/Leafly APIs require partner approval | Default to Dutchie-embedded menus + direct site scraping; treat APIs as unavailable |
| First scraper implementation | CSS selector fragility, silent zero-result failures | Semantic selectors + validation layer + `last_scraped_at` timestamps from day one |
| Distance filtering | Zip centroid geocoding errors at boundary | Geocode all addresses to lat/lng; hardcode 34982 centroid |
| Multi-source scraping | Duplicate deals from same dispensary on multiple platforms | Canonical dispensary ID in data model before first scraper ships |
| Dashboard display | Stale data presented as current | Show freshness timestamp per source; flag data older than 26h |
| Florida regulatory context | Assuming recreational rules apply | Medical-only market; some deal pages may be gated behind card verification |

---

## Sources

- Twilio cannabis ban: [MJBizDaily — Twilio cuts service to cannabis industry](https://mjbizdaily.com/text-messaging-provider-twilio-cuts-service-to-cannabis-industry/) | [Twilio Help — Cannabis messaging policy](https://help.twilio.com/articles/1260804628349-Can-I-send-cannabis-or-CBD-related-messaging-traffic-on-Twilio-) | MEDIUM confidence (official Twilio policy page, verified)
- Cannabis SMS alternatives: [Cannabis Creative — SMS Platforms](https://cannabiscreative.com/blog/what-sms-platforms-are-cannabis-friendly/) | LOW confidence (single source, no independent verification)
- Weedmaps API partner requirement: [Weedmaps Developer Onboarding](https://developer.weedmaps.com/docs/onboarding-process) | HIGH confidence (official developer docs)
- Weedmaps API versioning and deprecation: [Weedmaps Versioning Docs](https://developer.weedmaps.com/docs/versioning) | HIGH confidence (official developer docs)
- Dutchie scraping and ToS: [Dutchie Terms of Service](https://dutchie.com/terms) | [Dutchie Scraper on Apify](https://apify.com/tfmcg3/dutchie-dispensary-scraper) | MEDIUM confidence
- Scraper fragility patterns: [ProWebScraper — Why Scrapers Break](https://prowebscraper.com/articles/scraper-breakage) | [BinaryBits — Scraper Breakage](https://binarybits.co/blog/why-web-scraper-keeps-breaking) | MEDIUM confidence (general scraping community knowledge)
- Florida Amendment 3 failure: [Ballotpedia](https://ballotpedia.org/Florida_Amendment_3,_Marijuana_Legalization_Initiative_(2024)) | [Axios Miami](https://www.axios.com/local/miami/2024/11/06/florida-amendment-3-recreational-marijuana-fails) | HIGH confidence (multiple news sources)
- Port St. Lucie dispensary count: [Weedmaps PSL listings](https://weedmaps.com/dispensaries/in/united-states/florida/port-st-lucie) | MEDIUM confidence (real-time listing, count may vary)
- Silent data failure risks: [Monte Carlo — Stale Data](https://www.montecarlodata.com/blog-stale-data/) | MEDIUM confidence
