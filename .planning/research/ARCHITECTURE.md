# Architecture Patterns

**Domain:** Personal deal aggregation dashboard — single-user, self-hosted
**Researched:** 2026-04-10

---

## Recommended Architecture

A four-layer pipeline: **Scraper → Store → Server → Front-end**, with a side channel for **SMS alerts**. Each layer has a single, clear job. Nothing crosses boundaries except through well-defined data structures.

```
┌─────────────────────────────────────────────────────────────┐
│                        SCHEDULER                            │
│           (APScheduler or system cron — daily)              │
└────────────────────────┬────────────────────────────────────┘
                         │ triggers
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   SCRAPER LAYER                             │
│                                                             │
│  scrape_weedmaps.py   scrape_leafly.py   scrape_dutchie.py  │
│  ─────────────────────────────────────────────────────────  │
│  Each scraper:                                              │
│  1. Fetches deal/menu data from one source                  │
│  2. Normalizes to canonical Deal schema                     │
│  3. Writes to SQLite via shared db.py module                │
└────────────────────────┬────────────────────────────────────┘
                         │ writes normalized Deal rows
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                               │
│                  deals.db (SQLite)                          │
│                                                             │
│  deals table        dispensaries table    scrape_log table  │
│  ─────────────────────────────────────────────────────────  │
│  Canonical schema — all sources land here in the same shape │
└──────────────┬──────────────────────┬───────────────────────┘
               │ reads                │ reads (alert check)
               ▼                      ▼
┌──────────────────────┐   ┌──────────────────────────────────┐
│   FLASK SERVER       │   │       ALERT ENGINE               │
│   (app.py)           │   │       (alerts.py)                │
│                      │   │                                  │
│  GET /               │   │  Run after each scrape cycle     │
│  GET /api/deals      │   │  Check deals against rules       │
│  POST /api/refresh   │   │  If match: send SMS via Twilio   │
│  GET /api/status     │   │  Log sent alerts (no duplicates) │
└──────────┬───────────┘   └──────────────────────────────────┘
           │ serves
           ▼
┌─────────────────────────────────────────────────────────────┐
│                  FRONT-END LAYER                            │
│         index.html + dashboard.js + style.css               │
│                                                             │
│  Static files served by Flask                               │
│  Fetches /api/deals on load and on manual refresh click     │
│  Client-side filtering by category, dispensary, deal type   │
│  Shows last-refreshed timestamp from /api/status            │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

| Component | Responsibility | Communicates With | Does NOT Do |
|-----------|---------------|-------------------|-------------|
| Scheduler | Fires scrape job on schedule (daily + on-demand trigger) | Calls scraper layer | Knows nothing about data shape |
| Scraper modules | Fetch raw data from one source, normalize, persist | Writes to SQLite via db.py | Sends alerts, renders HTML |
| db.py | Single module wrapping all SQLite access | All components that touch DB | Business logic, HTTP |
| Flask server | Serves HTML, exposes JSON API, proxies manual refresh | Reads SQLite, triggers scrape | Scrapes, sends SMS |
| Alert engine | Runs deal matching rules, sends Twilio SMS if match | Reads SQLite, calls Twilio API | Renders anything |
| Front-end | Renders deal cards, handles filtering, refresh button | Calls Flask /api/* endpoints | Hits dispensary sites directly |

---

## Data Flow

```
Dispensary site / Weedmaps / Leafly / Dutchie
         │
         │  HTTP (Playwright or requests + BeautifulSoup)
         ▼
  [Scraper Module]
         │
         │  INSERT/UPSERT normalized Deal rows
         ▼
   deals.db (SQLite)
         │
         ├──── Flask reads deals ──── JSON response ──── dashboard.js renders
         │
         └──── Alert engine reads deals
                    │
                    │  Twilio REST API
                    ▼
              SMS to Jared's phone
```

**Direction is strictly one-way at each layer.** The front-end never writes to the DB. The scraper never sends SMS. The alert engine never renders HTML. This makes each component replaceable without touching the others.

---

## Canonical Deal Schema

Every scraper outputs this shape before touching the DB. Source normalization happens inside each scraper, not in the DB layer.

```python
{
  "id": "weedmaps_trulieve_psl_flower_001",  # source:dispensary:product hash
  "dispensary_id": "trulieve_port_st_lucie",
  "dispensary_name": "Trulieve",
  "dispensary_address": "...",
  "distance_miles": 4.2,
  "source": "weedmaps",                       # weedmaps | leafly | dutchie | direct
  "product_name": "Blue Dream 3.5g",
  "category": "flower",                       # flower | concentrate | edible | vape | tincture | topical | other
  "brand": "Trulieve",
  "price_cents": 2500,                        # always store as cents, never floats
  "original_price_cents": 4000,
  "discount_pct": 37,
  "price_per_gram_cents": 714,               # computed at insert time
  "thc_pct": 22.4,
  "deal_text": "37% off top shelf flower",
  "deal_type": "sale",                        # sale | bundle | daily_special | clearance
  "in_stock": true,
  "scraped_at": "2026-04-10T08:00:00Z",
  "expires_at": null                          # null if unknown
}
```

---

## Data Storage Approach

**Use SQLite. Single file. No server process.**

- `deals.db` lives in the project root
- Three tables: `dispensaries`, `deals`, `scrape_log`
- UPSERT on `deals.id` (no duplicates across runs)
- `scrape_log` records each run: source, start time, end time, rows upserted, error message if any
- No ORM — raw `sqlite3` module. Simple enough that an ORM adds ceremony without value.
- Keep 14 days of deals (delete rows where `scraped_at < now - 14 days` on each run). Stale data has no value.

**No JSON files for deal data.** JSON files as the primary store create race conditions on refresh and make querying/filtering require loading everything into memory. SQLite handles concurrent reads from Flask + the scraper without locking issues for this traffic level.

---

## Suggested Build Order

Dependencies drive this order. Each phase unlocks the next.

```
Phase 1: Data Layer + one scraper
  ├── Define canonical Deal schema
  ├── Create SQLite schema + db.py module
  └── Write one working scraper (Weedmaps first — most FL dispensaries listed)
      GATE: Can we get deal data into the DB for 34982-area dispensaries?

Phase 2: Flask server + static dashboard
  ├── GET /api/deals endpoint (reads from SQLite)
  ├── GET /api/status (last scrape time, row count)
  ├── index.html + deal card rendering
  └── Client-side category/dispensary filtering
      GATE: Jared can see deal cards in browser

Phase 3: Scheduler + manual refresh
  ├── APScheduler in Flask process for daily 6am run
  └── POST /api/refresh endpoint triggers scraper inline
      GATE: Data updates without touching terminal

Phase 4: Additional scrapers
  ├── Leafly scraper (normalized to same schema)
  └── Dutchie scraper (normalized to same schema)
      GATE: More dispensaries covered, duplicates handled by UPSERT on id

Phase 5: SMS alerts
  ├── Alert rules config (YAML or simple Python dict)
  ├── alerts.py — post-scrape rule evaluation
  └── Twilio send + alert_log to prevent re-alerting same deal
      GATE: Jared gets texts for notable deals

Phase 6: Polish
  ├── Deal quality scoring (price per gram percentile)
  ├── Distance display, dispensary info cards
  └── Error display in dashboard when scrape fails
```

**Why this order:**
- Phase 1 de-risks the hardest unknown (can we actually scrape FL dispensary data?) before building anything else
- Phase 2 creates visible progress fast — working dashboard with real data
- Phase 3 adds automation but doesn't block the core value
- Phase 4 is additive — more sources don't break existing structure
- Phase 5 last because it requires external account (Twilio) and is optional for core value

---

## Anti-Patterns to Avoid

### Scraping directly from the front-end
**What goes wrong:** Browser CORS restrictions block cross-origin requests to dispensary sites. Rate limiting hits the user's session. No caching possible.
**Instead:** All scraping server-side only. Front-end gets pre-fetched, cached data from Flask.

### One monolithic scraper for all sources
**What goes wrong:** One broken site stops all data collection. Hard to add new sources without touching working code.
**Instead:** One Python module per source. Shared `db.py` and canonical schema are the only coupling.

### Storing prices as floats
**What goes wrong:** `$24.99` becomes `24.990000000003` in calculations. Price-per-gram math produces garbage.
**Instead:** Store all prices as integer cents. Divide only at display time.

### Running scraper inside the Flask request handler synchronously
**What goes wrong:** Manual refresh button holds the HTTP connection open for 30-120 seconds while scraping runs. Browser times out, user thinks it broke.
**Instead:** POST /api/refresh returns 202 immediately, runs scraper in a background thread or subprocess. Front-end polls /api/status for completion.

### No deduplication across sources
**What goes wrong:** Trulieve appears on both Weedmaps and Leafly. Same product shows twice (or 6x) in the dashboard.
**Instead:** Canonical `id` is a hash of `dispensary_slug + product_slug`. UPSERT on id. Last-scraped data wins.

---

## Scalability Considerations

This is a single-user local tool. The scalability concern is **reliability and maintainability**, not traffic.

| Concern | For this project | If it grew |
|---------|-----------------|------------|
| Scrape failures | Log error to scrape_log, show warning in dashboard, keep last good data | Add retry with backoff |
| Dispensary site changes | Scraper breaks silently — log + dashboard warning | Automated scrape health checks |
| Data volume | 20 dispensaries x 200 products = 4,000 rows/day. SQLite handles millions. No concern. | Postgres if multi-user |
| SMS flooding | alert_log table with sent_at — skip if same deal alerted within 24h | Rate limiting |
| Scraper blocking | FL dispensaries may block scrapers — use Playwright with delays + user-agent rotation | Residential proxies |

---

## Sources

- Weedmaps scraper structure: [Apify Weedmaps Dispensary Scraper](https://apify.com/shahidirfan/weedmaps-dispensary-scraper/api/openapi)
- Dutchie scraper structure: [Apify Dutchie Dispensary Menu Scraper](https://apify.com/tfmcg3/dutchie-dispensary-scraper/api/openapi)
- Leafly scraper: [Apify Leafly Scraper](https://apify.com/paradox-analytics/leafly-scraper)
- Flask + APScheduler cron pattern: [flask-crontab PyPI](https://pypi.org/project/flask-crontab/)
- Twilio SMS Python integration: [Twilio SMS quickstart](https://www.twilio.com/docs/messaging/quickstart)
- SQLite for scraped data: [Web Scraping to SQL — Crawlbase](https://crawlbase.com/blog/web-scraping-to-sql-store-and-analyze-data/)
