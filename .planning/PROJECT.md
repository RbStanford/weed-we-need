# Jared's Dispensary Deals Dashboard

## What This Is

A personal deals dashboard for Jared that aggregates marijuana dispensary menus, deals, and specials from dispensaries within a 20-mile radius of zip code 34982 (Port St. Lucie, FL). It presents a browsable, filterable HTML dashboard with daily auto-refresh and on-demand refresh, plus SMS alerts when notable deals drop.

## Core Value

Jared can see all current dispensary deals in one place so he makes informed buying decisions — what to buy and where to buy it to save money.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Aggregate deals/menus from dispensaries within 20 miles of 34982
- [ ] Display all product categories (flower, concentrates, edibles, etc.) with filtering
- [ ] Auto-refresh data daily + manual refresh button
- [ ] Show deal quality indicators (price per gram, percentage off, etc.)
- [ ] SMS alerts for notable deals via text message
- [ ] Single-user HTML dashboard — no login required
- [ ] Dispensary info (name, location, distance from 34982)

### Out of Scope

- Multi-user accounts or authentication — single user, just Jared
- Mobile app — web dashboard is sufficient
- Purchase/ordering integration — Jared buys in person
- Price history tracking — v2 consideration
- Dispensary reviews or ratings — not a review platform

## Context

- Jared is in the 34982 (Port St. Lucie, FL) area
- Florida has a regulated medical/recreational marijuana market with dispensaries operating storefronts and online menus
- Most FL dispensaries publish deals on their websites and through aggregators like Leafly, Weedmaps, and Dutchie
- Data sourcing strategy TBD — research phase will determine best approach (scraping vs APIs vs aggregators)
- Dashboard will be hosted locally or on a simple server — just for Jared
- SMS delivery mechanism TBD — could use Twilio, existing SAM SMS infrastructure, or similar

## Constraints

- **Data Access**: Must find reliable, scrapable/API-accessible sources for dispensary deal data
- **Geography**: 20-mile radius from 34982
- **Freshness**: Data must refresh at least daily
- **Single User**: No auth complexity — private URL or local hosting
- **Legal**: Florida dispensary data only, publicly available information

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SMS for alerts (not email) | Jared prefers text — immediate, mobile | — Pending |
| No auth | Single user, simplicity over security | — Pending |
| All product categories | Jared wants to see everything, filter by interest | — Pending |
| 20-mile radius | Covers dispensaries Jared would actually drive to | — Pending |

---
*Last updated: 2026-04-10 after initialization*
