# Feature Landscape: Dispensary Deal Aggregator

**Domain:** Cannabis dispensary deal aggregation dashboard (personal use)
**Researched:** 2026-04-10
**Sources surveyed:** Leafly Deals, Weedmaps Deals, CannaSaver/CannaPages, CannaDealsFL, THCHunter, flcannabisdeals.org, BudDocs

---

## Table Stakes

Features users expect from any deal aggregator. Missing = product feels broken or useless.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Deal cards with dispensary name + deal title | Core display unit — every aggregator has this | Low | Must show who is running the deal |
| Discount amount or % shown prominently | Users need to know the value at a glance | Low | Both formats exist: "50% OFF" or "$10 off $50" |
| Product category labels on each deal | Flower vs. concentrate vs. edible — different buying decisions | Low | Standard 6: Flower, Concentrate, Edible, Vape/Cart, Pre-roll, Topical |
| Dispensary distance from user location | Users only care about dispensaries they will drive to | Low | Hard-code origin as 34982; show miles |
| Last-updated / freshness indicator | Stale data is worse than no data — users need to trust it | Low | "Last refreshed: 4h ago" pattern seen on every aggregator |
| Manual refresh button | Users want to pull current data on demand | Low | Supplement daily auto-refresh |
| Deal type label | BOGO vs. % off vs. bundle vs. new patient — drives buying decision | Low | Enumerated set, not free text |
| Dispensary operating hours or "open now" indicator | A deal is useless if the store is closed | Medium | Requires hours data per location |
| Filter by product category | First thing every user does — "show me flower deals" | Low | Checkbox or tab filter |
| Filter by dispensary / chain | Users have preferred dispensaries | Low | Multi-select by chain name |

---

## Differentiators

Features that go beyond what aggregators typically offer. High value for a personal tool precisely because public aggregators don't do these well.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Price-per-gram calculation | Converts deals into comparable unit pricing — no aggregator does this well | Medium | Requires structured product weight + price data; calculate on ingest |
| Deal quality / value score | Surfaces "actually good" deals vs. noise; CannaSaver uses a flame system, but it's opaque | Medium | Custom scoring: base price + discount depth + category weight |
| SMS alert for high-value deals | Immediate notification when a qualifying deal drops — no checking required | Medium | Twilio integration; configurable threshold (e.g., score > 80, or flower > 30% off) |
| Deal type taxonomy with named Florida specials | FL dispensaries run recurring named deals (Trulieve Tuesdays, MUV Mondays, AYR flash sales) — surface pattern | Low | Tag deals by recurring vs. one-time |
| Customer segment tagging | Veteran / senior / new patient discounts are structurally different from product deals — separate them | Low | THCHunter does this well; useful to filter out discounts Jared can't use |
| Deal expiration / time-remaining indicator | Urgency signal — "expires tonight" changes behavior | Low | Requires expiration data from source; fallback to "posted X hours ago" |
| Sort by deal value (not just recency) | Let Jared see best deals first, not just newest | Low | Trivial once value scoring exists |
| Deal deduplication | Same chain runs same deal at 20 FL locations — show once, not 20 cards | Low | Group by chain + deal text; show location count |
| "Hot right now" section | Surfaced high-score deals in a hero section above the fold | Low | Subset of value scoring; just top-N display |
| Deal history / previously seen indicator | Distinguish genuinely new deals from recurring ones Jared has already evaluated | Medium | Requires local state (SQLite or JSON); v1.5 complexity |

---

## Anti-Features

Things to deliberately NOT build for a single-user personal tool. These are present on public aggregators because they serve business models or multi-user needs that don't apply here.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| User accounts / login / registration | Single user — Jared. Auth adds complexity with zero benefit | Private URL or local-only hosting |
| User reviews or ratings of dispensaries | Not a review platform; Leafly/Weedmaps already do this | Link out to Weedmaps/Leafly for social proof |
| Loyalty points tracking | Each dispensary has their own program; aggregating them requires accounts at each chain | Out of scope — Jared manages this in-dispensary |
| Online ordering / cart integration | Jared buys in person; ordering requires dispensary API access and legal compliance | Deep-link to dispensary website instead |
| Delivery toggle | Jared drives to dispensaries per PROJECT.md | Remove clutter; in-store only |
| Multi-dispensary comparison for same SKU | Requires canonical product catalog matching across chains — massive data problem | Focus on deal surfacing, not SKU-level price comparison |
| Push notifications (browser/app) | SMS handles this per requirements; browser push requires service worker and user permission flow | SMS via Twilio only |
| Social features (sharing, comments) | Single user; no audience | N/A |
| Email digest / newsletter format | SMS was explicitly chosen per PROJECT.md; email adds a second channel | SMS only |
| Price history charts | Explicitly deferred to v2 in PROJECT.md | Track data in background for future use; don't build UI yet |
| Strain encyclopedia / strain info | Leafly does this; not a research tool | Link out to Leafly strain pages if needed |
| Advertising / sponsored deals | Single-user personal tool — no business model needed | Show all deals equally; sort by value |

---

## Feature Dependencies

```
Deal cards (display)
  -> Product category labels       (required for card display)
  -> Deal type label               (required for card display)
  -> Dispensary name + distance    (required for card display — distance needs geocode of 34982 origin)

Filter by category
  -> Product category labels       (upstream dependency)

Filter by dispensary
  -> Dispensary name               (upstream dependency)

Price-per-gram calculation
  -> Structured product data       (weight in grams + sale price — may not always be available from source)
  -> Graceful fallback when weight data missing

Deal value / quality score
  -> Discount % or dollar off      (required input)
  -> Product category              (category weights differ: flower scored differently than topicals)
  -> Price-per-gram                (optional but improves score quality)

SMS alert for hot deals
  -> Deal value score              (trigger threshold)
  -> Twilio or SMS infrastructure  (delivery mechanism — SAM SMS bot exists on machine)
  -> Deduplication                 (don't re-alert on same deal)

Sort by deal value
  -> Deal value score              (upstream dependency)

"Hot right now" section
  -> Deal value score              (upstream dependency)

Deal deduplication
  -> Chain name normalization      (same chain, different location names)
  -> Deal text fingerprinting      (hash or fuzzy match on deal description)

Deal expiration indicator
  -> Expiration data from source   (often absent — fallback to post timestamp + 24h assumption)

Last-updated indicator
  -> Refresh timestamp from ingest pipeline
```

---

## Deal Type Taxonomy

Every aggregator uses some version of this taxonomy. Jared's tool should label each deal on ingest.

| Deal Type | Description | FL Examples |
|-----------|-------------|-------------|
| Storewide % off | Everything in store at a discount | "20% off everything" — common on named days |
| Category % off | One product type discounted | "35% off all flower" |
| BOGO | Buy one get one free or near-free | "BOGO pre-rolls", "buy 2 get 1" |
| Bundle / multi-buy | Fixed price for quantity | "3 x 1g concentrates for $60" |
| New patient | First visit only | Common across all FL chains — Jared may only use once per chain |
| Renewal | Annual MMJ card renewal | Typically 20-25% off one purchase |
| Demographic | Veteran / senior / SNAP / industry worker | Permanent discount; not time-sensitive deal |
| Flash / limited-time | Hours-only sale | BudDocs Florida Flash Deals; high SMS alert value |
| Birthday | Month-of-birthday bonus | Low actionability unless month matches |
| Loyalty / reward | Points-based free product | Jared manages in-dispensary |
| Holiday | 4/20, Green Wednesday, 7/10 | Highest discount days; worth flagging in calendar |

---

## Product Category Standard

Consistent across Leafly, Weedmaps, THCHunter, CannaDealsFL:

| Category | Sub-types (optional) |
|----------|----------------------|
| Flower | Indica / Sativa / Hybrid (optional strain name) |
| Concentrate | Wax, Shatter, Live Resin, Rosin, Badder, Sugar |
| Vape / Cartridge | 510 cart, All-in-one, Disposable |
| Pre-roll | Singles, Multi-packs, Infused |
| Edible | Gummies, Chocolates, Beverages, Capsules |
| Topical | Balm, Patch, Spray |
| Tincture / Oral | Oil drops, Sublingual |
| Accessory | Not relevant for deal value — deprioritize display |

---

## MVP Feature Set Recommendation

Build these in phase 1 — everything else is iteration.

**Prioritize:**
1. Deal cards with: dispensary name, distance, deal title, product category, deal type, discount, timestamp
2. Filter by product category (tabs or checkboxes)
3. Filter by dispensary/chain (multi-select)
4. Last-refreshed indicator + manual refresh button
5. Deal deduplication (chain-level grouping)
6. Customer segment tagging (so Jared can hide "new patient only" deals he can't use)

**Phase 2 additions (after data pipeline is proven):**
- Price-per-gram calculation (requires structured weight + price data)
- Deal value score
- Sort by value
- "Hot right now" hero section
- SMS alert via Twilio (depends on score)

**Defer:**
- Deal expiration timer: data often not available from scraped sources; post timestamp + 24h heuristic is good enough for v1
- Deal history / "seen before" indicator: needs persistent local state, low priority until data is stable
- Price history: explicitly v2 per PROJECT.md

---

## Sources

- [Leafly Deals](https://www.leafly.com/deals) — product categories, deal types, strain phenotype filters
- [Weedmaps Deals](https://weedmaps.com/deals) — in-store vs. online deals, trending section, star ratings
- [CannaDealsFL](https://cannadealsfl.com/) — FL-specific aggregator; "just dropped" / "featured" / "recent" time sections; hourly refresh
- [THCHunter Florida Sales](https://thchunter.com/florida/sales/) — FL chain coverage, city/county filter, demographic discount types, 485 active deals across 16 chains
- [flcannabisdeals.org](https://flcannabisdeals.org/todays-florida-dispensary-deals/) — image-based deal aggregation; simpler UX
- [CannaSaver / CannaPages](https://deals.cannapages.com/) — flame-based "hot deal" scoring concept, printable coupons, ounce deal specialty section
- [BudDocs Flash Deals](https://buddocs.org/flashdeals/) — Florida-specific flash deal category
