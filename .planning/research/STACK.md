# Technology Stack: Dispensary Deals Dashboard

**Project:** Jared's Dispensary Deals Dashboard
**Researched:** 2026-04-10
**Domain:** Personal cannabis deals aggregator, single user, self-hosted

---

## Critical Context: Data Sourcing Is the Hard Problem

Standard web dashboard tech is trivial. The irreversible architectural decision is how data gets collected. Everything else flows from that choice. This section front-loads data sourcing before the rest of the stack.

---

## Data Sourcing Strategy

### Platform Landscape for Florida Dispensaries

Florida dispensaries near 34982 (Port St. Lucie) in the 20-mile radius include:

| Chain | Likely Menu Platform | Notes |
|-------|---------------------|-------|
| Trulieve | Dutchie | Trulieve.com checkout confirmed Dutchie-powered; multiple FL locations |
| Curaleaf | iHeartJane | iheartjane.com/stores/[id]/curaleaf-[loc]/menu confirmed for FL locations |
| AYR Cannabis | Weedmaps listing + own site | AYR lists on Weedmaps; online ordering via own site |
| MUV (AYR-owned) | Leafly + own site | MUV locations appear on Leafly |
| Sunnyside | Own site | Sunnyside.shop has direct online ordering |
| Surterra | Own site | surterra.com has direct menus |
| Cookies FL | Own site | cookiesflorida.co direct menu |

**Confidence:** MEDIUM — platform assignments derived from search results and URL patterns, not direct verification of every PSL-area location. Verify by loading each dispensary's menu page and checking the iframe source or footer attribution.

### Option A: Weedmaps Scraping (RECOMMENDED PRIMARY SOURCE)

**What it is:** Weedmaps aggregates 29+ dispensary listings for Port St. Lucie. Their public-facing site exposes an internal REST API at `api.weedmaps.com` that the browser calls when loading listings pages.

**Why it works:** Multiple commercial scrapers (Apify, Piloterr, Bright Data) have built and actively maintained Weedmaps scrapers as of 2025-2026, confirming the underlying data is accessible via HTTP. The `/listings` and menu endpoints are not the official partner API — they are the same endpoints the Weedmaps website uses to render pages, making them technically public (though ToS-restricted).

**What you get:** Dispensary name, address, hours, deal/specials text, menu items, prices, categories, distance filtering via lat/lon bounding box.

**The catch:** Weedmaps explicitly prohibits scraping in their Developer Terms and is not onboarding new API partners ("at this time, we are not onboarding new integrations" per developer.weedmaps.com). For personal/private use with reasonable request rates, the practical risk is low, but this is not a sanctioned use.

**Implementation approach:**
- Use Playwright (headless Chromium) to load `weedmaps.com/dispensaries/in/united-states/florida/port-st-lucie`
- Intercept or replay the `api.weedmaps.com` XHR calls that return JSON
- Parse deal/specials data from the JSON response
- No need to parse HTML — the raw API response is structured JSON

**Confidence:** MEDIUM — confirmed by indirect evidence (scraper market exists, ToS language exists); specific endpoint structure needs validation by opening browser DevTools on the Weedmaps PSL page.

### Option B: Leafly Scraping (RECOMMENDED SECONDARY SOURCE)

**What it is:** Leafly has a deals aggregator page at `leafly.com/deals` and dispensary pages with specials. Their internal `searchThisArea` API call (discovered via network traffic analysis) returns JSON for dispensaries in a lat/lon rectangle.

**Why it works:** The `searchThisArea` endpoint has been documented by independent researchers (scottbutters.com, Medium tutorials) and returns structured data including deals. Leafly's official API (requires POS partner approval) is separate and inaccessible — but the browser-facing internal API is reachable without credentials.

**What you get:** Dispensary list, deals/specials for each location, product data for MUV and Curaleaf locations that list on Leafly.

**The catch:** Leafly ToS prohibits automated scraping. Same personal-use caveat as Weedmaps. Also, not all FL chains maintain active Leafly menus — Trulieve in particular manages its own menu on trulieve.com.

**Confidence:** MEDIUM — internal API endpoint confirmed by multiple blog posts, but Leafly may have changed endpoints since those were written. Needs live validation.

### Option C: iHeartJane Public Store API (SUPPLEMENTARY)

**What it is:** iHeartJane exposes a semi-public store API at `iheartjane.com/v1/stores/[store_id]/` that returns product and deal data. Finding the store_id requires inspecting any iHeartJane-embedded page (F12 → look for the store ID in network requests or the iframe URL).

**Why it works:** The endpoint has been found and documented by a community GitHub project (`rapples/iheartjane-openai`, `SnarlsBarkely/JaneScraper`). iHeartJane's DM SDK docs implicitly confirm the `/v1/stores/` path. Curaleaf FL locations confirmed to use iHeartJane.

**What you get:** Full product menu, prices, categories, deal/discount flags for Curaleaf and any other iHeartJane-powered FL dispensaries.

**The catch:** Requires discovering store IDs per location. No bulk geo-search — you must know the store IDs in advance. Treat as a targeted supplement for chains confirmed on iHeartJane (primarily Curaleaf).

**Confidence:** MEDIUM — endpoint pattern confirmed by multiple community sources; stability over time uncertain.

### Option D: Direct Dispensary Website Scraping (FALLBACK)

**What it is:** Scrape Trulieve.com/promotions/florida, surterra.com, muvfl.com, ayrdispensaries.com etc. directly.

**Why it's a fallback:** Every site is different. Trulieve uses Dutchie for checkout but publishes promotions on their own `/promotions/` page which is static HTML. This is the most reliable long-term but most maintenance-intensive.

**Use case:** Trulieve (largest FL chain, doesn't maintain strong Weedmaps/Leafly listings). Also useful for chains that have deals published on their site but not on aggregators.

**Implementation:** Playwright for JS-rendered pages, requests + BeautifulSoup for static HTML. Per-site selectors needed.

**Confidence:** HIGH for feasibility; LOW for maintenance stability (sites change layouts).

### Option E: CannaDealsFL.com Scraping (OPPORTUNISTIC)

**What it is:** cannadealsfl.com is a Florida-specific aggregator that already pulls deals from 23+ FL dispensaries every 30 minutes. They have a deals page at `cannadealsfl.com/deals`.

**Why it's interesting:** If their deal data is accessible as structured HTML or JSON, you can piggyback on their aggregation work. This trades scraping many targets for scraping one.

**The catch:** You become dependent on a third-party site that could change or disappear. And their data is already processed/simplified — you may lose raw price-per-gram detail.

**Implementation:** Playwright or requests + BeautifulSoup to parse their deals listing.

**Confidence:** MEDIUM for feasibility — site confirmed active; HTML structure needs inspection.

### NOT Recommended: Official APIs

| Platform | Official API Status | Why Not |
|----------|-------------------|---------|
| Weedmaps | Closed — not onboarding new integrations | Partner-only, requires being a POS vendor |
| Leafly | Partner/POS only — requires `app_key`/`app_id` | Menu/Order API only, not for consumers |
| iHeartJane | Partner approval required | Must be a dispensary or approved POS |
| Dutchie | B2B only | Dispensary management, not consumer data |

**Recommended scraping stack:** Weedmaps (primary bulk source) + iHeartJane for Curaleaf locations + direct Trulieve promotions page. This covers the dominant FL chains.

---

## Recommended Full Stack

### Core Data Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.12 | Scraping, data pipeline, server | Mature ecosystem for scraping; all target libraries support it |
| Playwright (Python) | 1.44+ | Browser automation for JS-heavy sites | Weedmaps and Leafly render in JS; requests alone will fail. Playwright intercepts XHR calls which returns clean JSON without needing to parse HTML |
| httpx | 0.27+ | Async HTTP for static endpoints | For iHeartJane `/v1/stores/` calls which don't need a browser; faster than Playwright for known JSON APIs |
| BeautifulSoup4 | 4.12+ | HTML parsing for static pages | Trulieve promotions page, CannaDealsFL fallback — clean static HTML doesn't need a browser |
| SQLite (stdlib) | 3.x | Local data store | Zero infrastructure; stores deal records, dispensary list, last-scraped timestamps. Perfect for single-user use |

**Why Playwright over Selenium:** Playwright has better async support, faster page loads, and handles modern anti-bot measures better. Has native network request interception which is critical for extracting API calls made by Weedmaps. Confidence: HIGH (verified against current docs).

**Why SQLite over JSON files:** Structured queries for filtering by category/dispensary/date. Price-per-gram calculations. Easy to add price history later. Still zero-dependency infrastructure. Confidence: HIGH.

### Web Dashboard Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Flask | 3.0+ | HTTP server + API endpoints | Minimal overhead; exposes `/refresh` endpoint and serves the dashboard HTML. FastAPI is overkill here — no async needed for a personal dashboard |
| Flask-APScheduler | 1.13+ | Daily auto-refresh cron | Ties scheduler directly to the Flask process; no separate cron daemon needed on Windows |
| Vanilla HTML/CSS/JS | — | Frontend dashboard | No React/Vue overhead for a personal tool. Fetch API + `setInterval` for auto-poll. Tailwind CDN for clean styling without a build step |

**Why Flask over FastAPI:** This is a personal tool with zero concurrent users. Flask's simplicity wins. FastAPI's async and Pydantic are wasted complexity here. Confidence: HIGH.

**Why Flask-APScheduler over system cron:** On Windows (Sam's machine), Windows Task Scheduler is fragile for Python scripts. APScheduler runs in-process with the Flask app — one process to start, one to stop. Confidence: HIGH.

**Why vanilla JS over React:** Single-user dashboard. No state management complexity. The whole frontend can be one HTML file with inline JS. Ship faster, nothing to break. Confidence: HIGH.

### SMS Alerts

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Twilio Python SDK | 9.x | Send SMS alerts | Existing infrastructure already present in Sam's environment (SAM SMS bot in `Desktop/SAM SMS/`). Pay-per-message at $0.0083/SMS — negligible for a few alerts/day |
| twilio | 9.x | Python package | `pip install twilio` |

**Pricing note:** Twilio has no free tier after trial credit expires. A Twilio trial account provides free credit to test. For ongoing use, $0.0083/message + $1/month phone number = effectively free at personal volume (< 30 SMS/day).

**Alternative if Twilio is avoided:** ntfy.sh (free self-hosted push notifications) or email-to-SMS gateway (e.g., `number@tmomail.net` for T-Mobile). But Twilio is already on the machine and Rob has it configured — use it.

**Confidence:** HIGH — Twilio Python SDK is well-documented, stable, widely used.

### Geo-Filtering

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| uszipcode | 0.2.6+ | Zip-to-lat/lon lookup, no API key needed | Pure Python, uses a bundled SQLite database of US zip codes and coordinates. No external API calls, works offline |
| math (stdlib) | — | Haversine distance calculation | Standard library, 10 lines of code; no dependency needed for distance math |

**Why uszipcode over zipcodebase:** zipcodebase requires an API key and network call. uszipcode ships with all US zip code coordinates bundled — works offline, zero cost, no rate limits. Confidence: HIGH.

**Implementation pattern:**
```python
from uszipcode import SearchEngine
import math

def haversine_miles(lat1, lon1, lat2, lon2):
    R = 3958.8  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

search = SearchEngine()
origin = search.by_zipcode("34982")
# origin.lat, origin.lng available
```

---

## Full Dependency List

```bash
# Core scraping
pip install playwright==1.44.0
playwright install chromium

# HTTP + parsing
pip install httpx==0.27.0
pip install beautifulsoup4==4.12.3
pip install lxml==5.2.0  # faster BS4 parser

# Web server + scheduling
pip install flask==3.0.3
pip install flask-apscheduler==1.13.1

# SMS
pip install twilio==9.2.3

# Geo
pip install uszipcode==0.2.6
```

**No additional infrastructure required.** SQLite is stdlib. No Redis, no Celery, no Docker.

---

## What NOT to Use

| Technology | Why Not |
|------------|---------|
| Scrapy | Overkill for a handful of targets. Adds async complexity, Spider architecture is over-engineering for 5-10 sites |
| Selenium | Playwright is strictly better — faster, better interception, better async |
| Dash/Streamlit | Heavy Python dashboard frameworks; overkill for personal use. Adds 50+ MB of dependencies and a full reactive runtime for what is essentially a table with filters |
| PostgreSQL | Zero benefit over SQLite for single-user; adds infrastructure |
| Celery + Redis | Massively over-engineered for a daily cron job on a personal machine |
| Next.js / React | Build toolchain overhead for what should be one HTML file |
| Official Weedmaps/Leafly APIs | Closed to consumer-side developers; require being a POS vendor |
| Apify cloud scrapers | Paid service ($5+/month) for something trivially self-built; adds external dependency |

---

## Architecture Summary

```
[Scheduler: APScheduler daily + manual trigger]
    |
    v
[Scraper layer: Playwright + httpx + BeautifulSoup]
    | Weedmaps API interception
    | iHeartJane /v1/stores/ calls
    | Trulieve /promotions/ HTML
    |
    v
[SQLite DB: deals, dispensaries, products, last_scraped]
    |
    v
[Flask server]
    | GET /          → HTML dashboard (filter by category, dispensary, distance)
    | GET /api/deals → JSON for frontend fetch
    | POST /refresh  → trigger immediate re-scrape
    |
    v
[Browser: vanilla HTML/JS/CSS dashboard]

[Parallel: Twilio SMS] ← triggered when deal score exceeds threshold
```

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Web framework (Flask + APScheduler) | HIGH | Mature, well-documented, fits use case perfectly |
| SMS (Twilio) | HIGH | Already present on machine; SDK stable |
| Geo-filtering (uszipcode + haversine) | HIGH | Standard approach, verified on PyPI |
| Weedmaps data access | MEDIUM | Internal API confirmed by scraper market; specific endpoint needs live validation |
| Leafly data access | MEDIUM | Internal searchThisArea API documented but may have changed |
| iHeartJane data access | MEDIUM | Community-confirmed endpoint; stability uncertain |
| FL dispensary platform assignments | MEDIUM | Trulieve/Dutchie confirmed; others need spot-check |

---

## Sources

- [Leafly API Documentation (official)](https://help.leafly.com/hc/en-us/articles/20916238531603-Leafly-API-Documentation)
- [Weedmaps Developer Portal — "not onboarding new integrations"](https://developer.weedmaps.com/)
- [Weedmaps Developer Terms of Use](https://weedmaps.com/legal/developer-terms)
- [iHeartJane DM SDK Docs](https://dm-sdk-docs.iheartjane.com/docs/api/)
- [JaneScraper (community)](https://github.com/SnarlsBarkely/JaneScraper)
- [iHeartJane + OpenAI community project](https://github.com/rapples/iheartjane-openai)
- [Trulieve on Dutchie](https://dutchie.com/dispensary/trulieve-bristol)
- [Curaleaf on iHeartJane](https://www.iheartjane.com/stores/2224/curaleaf-melrose/menu)
- [CannaDealsFL — 30-minute aggregation from dispensary sites](https://cannadealsfl.com/)
- [FLCannabisDeals.org — FL deal aggregator](https://flcannabisdeals.org/)
- [Weedmaps Port St. Lucie listings](https://weedmaps.com/dispensaries/in/united-states/florida/port-st-lucie)
- [Playwright web scraping guide 2025](https://www.scraperapi.com/web-scraping/playwright/)
- [Flask-APScheduler PyPI](https://pypi.org/project/Flask-APScheduler/)
- [uszipcode PyPI](https://pypi.org/project/uszipcode/)
- [Twilio SMS pricing (US)](https://www.twilio.com/en-us/sms/pricing/us)
- [Apify Weedmaps scraper (confirms data accessible)](https://apify.com/parseforge/weedmaps-scraper/api/openapi)
- [Mining Leafly data via internal API (blog)](https://medium.com/@aandrei_38387/mining-leafly-data-ae87c4b73856)
