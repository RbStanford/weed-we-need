"""
The Weed We Need — Jared & Nicole's Daily Deal Report
Pulls deals from CannaDealsFL API, generates a mobile-friendly HTML page,
and deploys to Vercel.

Usage:
    python build_dashboard.py          # Generate HTML only
    python build_dashboard.py --push   # Generate + push to GitHub Pages
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

API_URL = "https://cannadealsfl.com/api/deals?limit=100&page=1"
OUTPUT_DIR = Path(__file__).parent / "docs"
OUTPUT_FILE = OUTPUT_DIR / "index.html"

# Jared's home: 4665 S 25th St, Fort Pierce, FL
JARED_LAT = 27.4175
JARED_LNG = -80.3535

# Dispensary chains with locations within 20 miles of Jared
# Source: Weedmaps discovery API, verified 2026-04-10
LOCAL_CHAINS = {
    "ayr", "cannabist", "cookies", "curaleaf", "fluent",
    "green dragon", "grow healthy", "growhealthy",
    "müv", "muv", "planet 13", "sanctuary",
    "sunnyside", "surterra", "trulieve",
}

# Nearby locations per chain — name, address, city, lat, lng
# Used for distance calc and Google Maps links
NEARBY_LOCATIONS = {
    "fluent": [
        ("FLUENT", "2509 S US Hwy 1", "Fort Pierce", 27.4220, -80.3310),
    ],
    "green dragon": [
        ("Green Dragon", "2217 S US Hwy 1", "Fort Pierce", 27.4250, -80.3300),
        ("Green Dragon", "2285 SE Federal Hwy", "Stuart", 27.1750, -80.2270),
    ],
    "trulieve": [
        ("Trulieve", "2200 S US Hwy 1", "Fort Pierce", 27.4260, -80.3300),
        ("Trulieve", "1858 SW Gatlin Blvd", "Port St. Lucie", 27.2631, -80.3395),
        ("Trulieve", "1707 SE Port St Lucie Blvd", "Port St. Lucie", 27.2780, -80.3240),
        ("Trulieve", "2100 SE Federal Hwy", "Stuart", 27.1850, -80.2400),
        ("Trulieve", "2443 SE Federal Hwy", "Stuart", 27.1710, -80.2270),
    ],
    "ayr": [
        ("AYR Cannabis", "4580 Okeechobee Rd", "Fort Pierce", 27.4310, -80.3800),
        ("AYR Cannabis", "1428 SE Village Green Dr", "Port St. Lucie", 27.2730, -80.3190),
        ("AYR Cannabis", "2419 SE Federal Hwy", "Stuart", 27.1720, -80.2260),
    ],
    "müv": [
        ("MUV", "1006 S US Hwy 1", "Fort Pierce", 27.4360, -80.3255),
        ("MUV", "1564 NW Gatlin Blvd", "Port St. Lucie", 27.2633, -80.3944),
        ("MUV", "3550 NW Federal Hwy", "Stuart", 27.2130, -80.2770),
    ],
    "muv": [
        ("MUV", "1006 S US Hwy 1", "Fort Pierce", 27.4360, -80.3255),
        ("MUV", "1564 NW Gatlin Blvd", "Port St. Lucie", 27.2633, -80.3944),
        ("MUV", "3550 NW Federal Hwy", "Stuart", 27.2130, -80.2770),
    ],
    "curaleaf": [
        ("Curaleaf", "5192 Okeechobee Rd", "Fort Pierce", 27.4320, -80.3950),
        ("Curaleaf", "1703 NW St Lucie West Blvd", "Port St. Lucie", 27.2830, -80.3890),
        ("Curaleaf", "3458 NW Federal Hwy", "Jensen Beach", 27.2620, -80.2370),
        ("Curaleaf", "4203 SE Federal Hwy", "Stuart", 27.1540, -80.2183),
    ],
    "sanctuary": [
        ("Sanctuary Cannabis", "5774 Okeechobee Rd", "Fort Pierce", 27.4330, -80.4130),
    ],
    "cookies": [
        ("Cookies", "1600 NW Courtyard Cir", "Port St. Lucie", 27.2770, -80.3980),
    ],
    "sunnyside": [
        ("Sunnyside", "1576 NW Gatlin Blvd", "Port St. Lucie", 27.2640, -80.3974),
    ],
    "surterra": [
        ("Surterra", "1752 SW Gatlin Blvd", "Port St. Lucie", 27.2640, -80.3290),
    ],
    "planet 13": [
        ("Planet 13", "3501 NW Federal Hwy", "Stuart", 27.2150, -80.2740),
    ],
    "growhealthy": [
        ("GrowHealthy", "3462 SE Federal Hwy", "Stuart", 27.1540, -80.2140),
    ],
    "grow healthy": [
        ("GrowHealthy", "3462 SE Federal Hwy", "Stuart", 27.1540, -80.2140),
    ],
    "cannabist": [
        ("Cannabist", "4203 SE Federal Hwy #103", "Stuart", 27.1540, -80.2183),
    ],
}


def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance in miles between two lat/lng points."""
    import math
    R = 3959
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def get_locations_html(chain_key, disp_name):
    """Build HTML for nearby locations as selectable buttons."""
    locations = NEARBY_LOCATIONS.get(chain_key, [])
    if not locations:
        return "", None, None

    # Sort by distance
    locs_with_dist = []
    for name, addr, city, lat, lng in locations:
        dist = haversine(JARED_LAT, JARED_LNG, lat, lng)
        locs_with_dist.append((dist, name, addr, city, lat, lng))
    locs_with_dist.sort()

    buttons = []
    for dist, name, addr, city, lat, lng in locs_with_dist:
        buttons.append(
            f'<button class="loc-btn" onclick="pickLocation(this)" '
            f'data-lat="{lat}" data-lng="{lng}" data-addr="{addr}, {city}" data-disp="{disp_name}">'
            f'<span class="loc-distance">{dist:.1f} mi</span> '
            f'<span class="loc-addr">{addr}, {city}</span>'
            f'</button>'
        )

    label = '<p class="loc-prompt">&#128205; Pick your location first:</p>' if len(buttons) > 1 else '<p class="loc-prompt">&#128205; Your nearest location:</p>'

    return f'{label}<div class="locations">{"".join(buttons)}</div>', locs_with_dist[0][4], locs_with_dist[0][5]


def fetch_deals():
    """Pull all active deals from CannaDealsFL API."""
    req = urllib.request.Request(
        API_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    deals = data.get("deals", [])
    print(f"Fetched {len(deals)} deals from CannaDealsFL")
    return deals


def parse_deals(raw_deals):
    """Normalize raw API data into clean deal objects."""
    parsed = []
    skipped = []
    for d in raw_deals:
        if not d.get("is_active"):
            continue

        dispensary = d.get("dispensary") or {}

        # Filter to only dispensaries with locations near 34982
        disp_name = (dispensary.get("name") or "").lower().strip()
        if not any(chain in disp_name for chain in LOCAL_CHAINS):
            skipped.append(dispensary.get("name", "Unknown"))
            continue
        category = d.get("product_category") or {}

        # Fix encoding issues (API returns mojibake for bullet chars)
        description = (d.get("description") or "").replace("\u00e2\u20ac\u00a2", "\u2022")
        title = (d.get("title") or "No title").replace("\u00e2\u20ac\u00a2", "\u2022")

        parsed.append({
            "title": title,
            "description": description,
            "dispensary_name": dispensary.get("name", "Unknown"),
            "dispensary_slug": dispensary.get("slug", ""),
            "dispensary_logo": dispensary.get("logo_url", ""),
            "dispensary_website": dispensary.get("website_url", ""),
            "dispensary_description": (dispensary.get("description") or "").replace("\u00e2\u20ac\u00a2", "\u2022"),
            "category_name": category.get("name", "Other"),
            "category_color": category.get("color", "#6b7280"),
            "category_icon": category.get("icon", ""),
            "discount_percentage": d.get("discount_percentage"),
            "discount_amount": d.get("discount_amount"),
            "original_price": d.get("original_price"),
            "sale_price": d.get("sale_price"),
            "image_url": d.get("image_url", ""),
            "slug": d.get("slug", ""),
            "created_at": d.get("created_at", ""),
            "is_verified": d.get("is_verified", False),
        })

    if skipped:
        print(f"Filtered out {len(skipped)} deals from dispensaries not near 34982: {', '.join(sorted(set(skipped)))}")

    # Sort by dispensary name then category
    parsed.sort(key=lambda x: (x["dispensary_name"].lower(), x["category_name"].lower()))
    return parsed


def build_html(deals, generated_at):
    """Generate self-contained mobile-friendly HTML dashboard."""

    # Group deals by dispensary
    by_dispensary = {}
    categories = set()
    for deal in deals:
        name = deal["dispensary_name"]
        if name not in by_dispensary:
            by_dispensary[name] = {
                "deals": [],
                "logo": deal["dispensary_logo"],
                "website": deal["dispensary_website"],
                "description": deal["dispensary_description"],
            }
        by_dispensary[name]["deals"].append(deal)
        categories.add(deal["category_name"])

    categories = sorted(categories)
    dispensary_count = len(by_dispensary)
    deal_count = len(deals)

    # Build deal cards HTML
    dispensary_sections = []
    for disp_name in sorted(by_dispensary.keys()):
        disp = by_dispensary[disp_name]
        cards_html = []
        for deal in disp["deals"]:
            # Badge for discount
            badge = ""
            if deal["discount_percentage"]:
                badge = f'<span class="badge badge-pct">{deal["discount_percentage"]}% OFF</span>'
            elif deal["discount_amount"]:
                badge = f'<span class="badge badge-amt">${deal["discount_amount"]} OFF</span>'

            verified = '<span class="verified" title="Verified">&#10003;</span>' if deal["is_verified"] else ""

            # Image
            img_html = ""
            if deal["image_url"]:
                img_src = deal["image_url"]
                if img_src.startswith("/"):
                    img_src = f"https://cannadealsfl.com{img_src}"
                img_html = f'<img src="{img_src}" alt="" class="deal-img" loading="lazy" onerror="this.style.display=\'none\'">'

            # Build tappable line items from description
            items_html = ""
            if deal["description"]:
                lines = [l.strip() for l in deal["description"].split("\n") if l.strip()]
                item_divs = []
                for line in lines:
                    clean = line.lstrip("•-* ").strip()
                    if clean:
                        item_divs.append(
                            f'<div class="deal-item" onclick="toggleItem(this)">'
                            f'<span class="item-check">&#128722;</span>'
                            f'<span class="item-text">{clean}</span>'
                            f'</div>'
                        )
                items_html = f'<div class="deal-items">{"".join(item_divs)}</div>'

            # Find closest location for this dispensary chain
            closest_lat, closest_lng = JARED_LAT, JARED_LNG
            chain_key_deal = deal["dispensary_name"].lower().strip()
            locs = NEARBY_LOCATIONS.get(chain_key_deal, [])
            if locs:
                best = min(locs, key=lambda l: haversine(JARED_LAT, JARED_LNG, l[3], l[4]))
                closest_lat, closest_lng = best[3], best[4]

            cards_html.append(f'''
            <div class="deal-card" data-category="{deal['category_name'].lower()}" data-disp="{deal['dispensary_name']}" data-lat="{closest_lat}" data-lng="{closest_lng}">
                {img_html}
                <div class="deal-content">
                    <div class="deal-header">
                        <span class="category-tag" style="background:{deal['category_color']}20; color:{deal['category_color']}">{deal['category_name']}</span>
                        {badge}
                        {verified}
                    </div>
                    <h3 class="deal-title">{deal['title']}</h3>
                    {items_html}
                </div>
            </div>''')

        website_link = ""
        if disp["website"]:
            website_link = f'<a href="{disp["website"]}" target="_blank" rel="noopener" class="disp-order-link">&#127807; Click Here To Order Now</a>'

        standing_deals = ""
        if disp["description"]:
            standing_deals = f'<p class="disp-standing">{disp["description"]}</p>'

        # Get nearby locations as selectable buttons
        chain_key = disp_name.lower().strip()
        locations_html, default_lat, default_lng = get_locations_html(chain_key, disp_name)

        dispensary_sections.append(f'''
        <section class="dispensary-section" data-dispensary="{disp_name.lower()}">
            <div class="disp-header">
                <div class="disp-info">
                    <img src="{disp['logo']}" alt="" class="disp-logo" onerror="this.style.display='none'">
                    <div>
                        <h2 class="disp-name">{'<a href="' + disp["website"] + '" target="_blank" rel="noopener" class="disp-name-link">' + disp_name + '</a>' if disp["website"] else disp_name}</h2>
                        {standing_deals}
                    </div>
                </div>
                {website_link}
            </div>
            {locations_html}
            <div class="deals-grid locked" data-disp="{disp_name}">
                <div class="locked-msg">&#128274; Select a location above to start shopping</div>
                {"".join(cards_html)}
            </div>
        </section>''')

    # Category filter buttons
    filter_buttons = ['<button class="filter-btn active" data-filter="all">All</button>']
    for cat in categories:
        filter_buttons.append(f'<button class="filter-btn" data-filter="{cat.lower()}">{cat}</button>')

    timestamp = generated_at.strftime("%B %d, %Y at %I:%M %p")

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>The Weed We Need</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        :root {{
            --bg: #f5f5f5;
            --surface: #fff;
            --surface2: #eee;
            --text: #1a1a1a;
            --text-muted: #666;
            --accent: #22c55e;
            --accent-dim: #16a34a;
            --border: #ddd;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            min-height: 100dvh;
            padding-bottom: env(safe-area-inset-bottom);
        }}

        .header {{
            position: sticky;
            top: 0;
            z-index: 100;
            background: var(--bg);
            border-bottom: 1px solid var(--border);
            padding: 16px;
        }}

        .header-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}

        .header h1 {{
            font-size: 20px;
            font-weight: 700;
            color: var(--accent);
        }}

        .stats {{
            font-size: 13px;
            color: var(--text-muted);
        }}

        .refresh-btn {{
            background: var(--surface2);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 13px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .refresh-btn:active {{
            background: var(--accent-dim);
        }}

        .filters {{
            display: flex;
            gap: 8px;
            overflow-x: auto;
            padding-bottom: 4px;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
        }}

        .filters::-webkit-scrollbar {{ display: none; }}

        .filter-btn {{
            background: var(--surface2);
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            white-space: nowrap;
            cursor: pointer;
            transition: all 0.15s;
        }}

        .filter-btn.active {{
            background: var(--accent);
            color: #000;
            border-color: var(--accent);
            font-weight: 600;
        }}

        .main {{
            padding: 16px;
            max-width: 700px;
            margin: 0 auto;
        }}

        .dispensary-section {{
            margin-bottom: 28px;
        }}

        .disp-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
            gap: 12px;
        }}

        .disp-info {{
            display: flex;
            gap: 10px;
            align-items: flex-start;
        }}

        .disp-logo {{
            width: 36px;
            height: 36px;
            border-radius: 8px;
            flex-shrink: 0;
            background: var(--surface2);
        }}

        .disp-name {{
            font-size: 18px;
            font-weight: 700;
        }}

        .disp-name-link {{
            color: var(--text);
            text-decoration: underline;
            text-decoration-color: var(--accent);
            text-underline-offset: 3px;
        }}

        .disp-standing {{
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 2px;
            line-height: 1.4;
        }}

        .disp-link {{
            font-size: 13px;
            color: var(--accent);
            text-decoration: none;
            white-space: nowrap;
            flex-shrink: 0;
            padding-top: 4px;
        }}

        .disp-order-link {{
            display: block;
            text-align: center;
            background: var(--accent);
            color: #fff;
            font-size: 16px;
            font-weight: 700;
            padding: 12px 16px;
            border-radius: 10px;
            text-decoration: none;
            margin-bottom: 12px;
        }}

        .disp-order-link:active {{
            opacity: 0.8;
        }}

        .hq-section {{
            margin-bottom: 24px;
            text-align: center;
        }}

        .hq-title {{
            font-size: 22px;
            font-weight: 800;
            color: var(--accent);
            margin-bottom: 4px;
            letter-spacing: 1px;
        }}

        .hq-subtitle {{
            font-size: 13px;
            color: var(--text-muted);
            margin-bottom: 10px;
        }}

        .hq-photo {{
            position: relative;
            border-radius: 12px;
            overflow: hidden;
            border: 2px solid var(--accent);
        }}

        .hq-photo img {{
            width: 100%;
            display: block;
        }}

        .hq-badge {{
            position: absolute;
            bottom: 12px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.8);
            color: var(--accent);
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 1px;
            border: 1px solid var(--accent);
            white-space: nowrap;
        }}

        .how-it-works {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 24px;
        }}

        .how-it-works h3 {{
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 10px;
            color: var(--text);
        }}

        .how-it-works ol {{
            padding-left: 20px;
            font-size: 14px;
            color: var(--text-muted);
            line-height: 1.8;
        }}

        .how-it-works li {{
            margin-bottom: 4px;
        }}

        .loc-prompt {{
            font-size: 13px;
            font-weight: 600;
            color: var(--text);
            margin-bottom: 6px;
        }}

        .locations {{
            display: flex;
            flex-direction: column;
            gap: 4px;
            margin-bottom: 12px;
        }}

        .loc-btn {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 14px;
            background: var(--surface);
            border: 2px solid var(--border);
            border-radius: 10px;
            color: var(--text);
            font-size: 14px;
            cursor: pointer;
            width: 100%;
            text-align: left;
            transition: all 0.15s;
        }}

        .loc-btn:active {{
            background: #f0fdf4;
        }}

        .loc-btn.selected {{
            border-color: var(--accent);
            background: #f0fdf4;
        }}

        .loc-distance {{
            font-weight: 700;
            color: var(--accent);
            min-width: 55px;
        }}

        .loc-addr {{
            flex: 1;
            color: var(--text-muted);
        }}

        .deals-grid.locked .deal-card {{
            opacity: 0.3;
            pointer-events: none;
        }}

        .locked-msg {{
            text-align: center;
            padding: 12px;
            font-size: 14px;
            color: var(--text-muted);
            font-weight: 600;
        }}

        .deals-grid:not(.locked) .locked-msg {{
            display: none;
        }}

        .deals-grid {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}

        .deal-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
        }}

        .deal-card.hidden {{
            display: none;
        }}

        .deal-img {{
            width: 100%;
            display: block;
        }}

        .deal-content {{
            padding: 12px 14px;
        }}

        .deal-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 6px;
            flex-wrap: wrap;
        }}

        .category-tag {{
            font-size: 11px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .badge {{
            font-size: 11px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 6px;
        }}

        .badge-pct {{
            background: #ef444420;
            color: #ef4444;
        }}

        .badge-amt {{
            background: #f59e0b20;
            color: #f59e0b;
        }}

        .verified {{
            color: var(--accent);
            font-size: 14px;
        }}

        .deal-title {{
            font-size: 15px;
            font-weight: 600;
            line-height: 1.3;
            margin-bottom: 4px;
        }}

        .deal-desc {{
            font-size: 13px;
            color: var(--text-muted);
            line-height: 1.5;
        }}

        .footer {{
            text-align: center;
            padding: 24px 16px 40px;
            font-size: 12px;
            color: var(--text-muted);
        }}

        .footer a {{
            color: var(--accent);
            text-decoration: none;
        }}

        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: var(--text-muted);
        }}

        .empty-state h3 {{
            font-size: 18px;
            margin-bottom: 8px;
            color: var(--text);
        }}

        .deal-items {{
            display: flex;
            flex-direction: column;
            gap: 4px;
            margin-top: 8px;
        }}

        .deal-item {{
            display: flex;
            align-items: flex-start;
            gap: 8px;
            padding: 8px 10px;
            border: 1px solid var(--border);
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            color: var(--text-muted);
            line-height: 1.4;
            transition: all 0.15s;
        }}

        .deal-item:active {{
            background: #f0fdf4;
        }}

        .deal-item.in-cart {{
            border-color: var(--accent);
            background: #f0fdf4;
            color: var(--text);
        }}

        .item-check {{
            font-size: 16px;
            flex-shrink: 0;
            opacity: 0.4;
        }}

        .deal-item.in-cart .item-check {{
            opacity: 1;
        }}

        .item-text {{
            flex: 1;
        }}

        .cart-btn {{
            margin-left: auto;
            background: #f0fdf4;
            border: 2px solid var(--accent);
            border-radius: 8px;
            padding: 5px 10px;
            font-size: 18px;
            cursor: pointer;
            transition: all 0.15s;
        }}

        .cart-btn.selected {{
            background: var(--accent);
            border-color: var(--accent);
        }}

        .deal-card.in-cart {{
            border-color: var(--accent);
            box-shadow: 0 0 0 2px rgba(34,197,94,0.3);
        }}

        .floating-cart {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: var(--accent);
            color: #fff;
            width: 56px;
            height: 56px;
            border-radius: 50%;
            display: none;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 200;
            border: none;
        }}

        .floating-cart.visible {{
            display: flex;
        }}

        .cart-count {{
            position: absolute;
            top: -4px;
            right: -4px;
            background: #ef4444;
            color: #fff;
            font-size: 12px;
            font-weight: 700;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .route-panel {{
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #fff;
            border-top: 2px solid var(--accent);
            border-radius: 16px 16px 0 0;
            padding: 20px;
            z-index: 300;
            display: none;
            max-height: 70vh;
            overflow-y: auto;
            box-shadow: 0 -4px 20px rgba(0,0,0,0.15);
        }}

        .route-panel.open {{
            display: block;
        }}

        .route-panel h3 {{
            font-size: 20px;
            margin-bottom: 4px;
            color: var(--text);
        }}

        .runner-picker {{
            display: flex;
            gap: 8px;
            margin-bottom: 14px;
        }}

        .runner-btn {{
            flex: 1;
            padding: 10px;
            border: 2px solid var(--border);
            border-radius: 10px;
            background: var(--surface);
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            text-align: center;
        }}

        .runner-btn.active {{
            border-color: var(--accent);
            background: rgba(34,197,94,0.1);
        }}

        .route-stop {{
            padding: 8px 0;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }}

        .route-stop .stop-num {{
            display: inline-block;
            width: 24px;
            height: 24px;
            background: var(--accent);
            color: #fff;
            border-radius: 50%;
            text-align: center;
            line-height: 24px;
            font-size: 12px;
            font-weight: 700;
            margin-right: 8px;
        }}

        .route-btn {{
            display: block;
            width: 100%;
            padding: 14px;
            margin-top: 16px;
            background: var(--accent);
            color: #fff;
            border: none;
            border-radius: 10px;
            font-size: 18px;
            font-weight: 700;
            cursor: pointer;
            text-align: center;
            text-decoration: none;
        }}

        .route-close {{
            float: right;
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: var(--text-muted);
        }}

        .route-overlay {{
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.4);
            z-index: 250;
            display: none;
        }}

        .route-overlay.open {{
            display: block;
        }}

        /* Light mode only */
    </style>
</head>
<body>
    <header class="header">
        <div class="header-top">
            <div>
                <h1>&#127807; The Weed We Need</h1>
                <p class="stats">Daily Deal Report &middot; {deal_count} deals &middot; {dispensary_count} dispensaries</p>
                <p class="stats">Updated {timestamp}</p>
            </div>
            <button class="refresh-btn" onclick="location.reload()">&#8635; Refresh</button>
        </div>
        <div class="filters">
            {"".join(filter_buttons)}
        </div>
    </header>

    <main class="main" id="deals-container">

<section class="how-it-works">
            <h3>&#128663; How The Weed Run Works</h3>
            <ol>
                <li><strong>Pick a location</strong> — tap which store you're going to</li>
                <li><strong>Tap the items you want</strong> — they turn green and go in your cart</li>
                <li><strong>Repeat</strong> at other dispensaries — build your full shopping list</li>
                <li>Tap the &#128663; button to see your list, then hit <strong>"Start The Weed Run"</strong> for the route</li>
            </ol>
        </section>

        {"".join(dispensary_sections)}
    </main>

    <footer class="footer">
        <p>Data from <a href="https://cannadealsfl.com" target="_blank">CannaDealsFL</a></p>
        <p>Made with &#10084;&#65039; by Rob</p>
    </footer>

    <button class="floating-cart" id="floatingCart" onclick="openRoutePanel()">
        &#128663;
        <span class="cart-count" id="cartCount">0</span>
    </button>

    <div class="route-overlay" id="routeOverlay" onclick="closeRoutePanel()"></div>
    <div class="route-panel" id="routePanel">
        <button class="route-close" onclick="closeRoutePanel()">&times;</button>
        <h3>&#127807; The Weed Run</h3>
        <div class="runner-picker">
            <button class="runner-btn active" id="runnerMe" onclick="pickRunner('I am')">&#128587; My Run</button>
            <button class="runner-btn" id="runnerOther" onclick="pickRunner('We are')">&#128107; Our Run</button>
        </div>
        <p id="runnerLabel" style="font-size:13px; color:#666; margin-bottom:12px;">I am making The Weed Run today</p>
        <div id="routeStops"></div>
        <a id="routeLink" class="route-btn" target="_blank" rel="noopener">&#128663; Start The Weed Run in Google Maps</a>
        <button class="route-btn" style="background:#ef4444; margin-top:8px;" onclick="clearCart()">Clear All</button>
    </div>

    <script>
        const HQ_LAT = {JARED_LAT};
        const HQ_LNG = {JARED_LNG};
        const cart = new Map();
        const selectedLocations = {{}}; // disp -> {{lat, lng, addr}}

        function pickLocation(btn) {{
            const disp = btn.dataset.disp;
            const lat = btn.dataset.lat;
            const lng = btn.dataset.lng;
            const addr = btn.dataset.addr;

            // Deselect siblings
            btn.closest('.locations').querySelectorAll('.loc-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');

            // Store selected location
            selectedLocations[disp] = {{ lat, lng, addr }};

            // Unlock the deals grid for this dispensary
            const section = btn.closest('.dispensary-section');
            const grid = section.querySelector('.deals-grid');
            grid.classList.remove('locked');

            // Update all deal cards in this section with the selected location
            grid.querySelectorAll('.deal-card').forEach(card => {{
                card.dataset.lat = lat;
                card.dataset.lng = lng;
            }});
        }}

        function toggleItem(el) {{
            const card = el.closest('.deal-card');
            const disp = card.dataset.disp;
            const lat = card.dataset.lat;
            const lng = card.dataset.lng;
            const text = el.querySelector('.item-text').textContent;
            const key = disp + '|' + lat + '|' + lng + '|' + text;

            if (cart.has(key)) {{
                cart.delete(key);
                el.classList.remove('in-cart');
            }} else {{
                cart.set(key, true);
                el.classList.add('in-cart');
            }}
            updateCartUI();
        }}

        function updateCartUI() {{
            const count = cart.size;
            document.getElementById('cartCount').textContent = count;
            document.getElementById('floatingCart').classList.toggle('visible', count > 0);
        }}

        function openRoutePanel() {{
            // Group by dispensary and get unique stops
            const stops = {{}};
            cart.forEach((_, key) => {{
                const [disp, lat, lng, ...textParts] = key.split('|');
                const text = textParts.join('|');
                if (!stops[disp]) stops[disp] = {{ lat: parseFloat(lat), lng: parseFloat(lng), items: [] }};
                stops[disp].items.push(text);
            }});

            // Sort stops by nearest-neighbor from HQ
            const sorted = [];
            const remaining = Object.entries(stops);
            let curLat = HQ_LAT, curLng = HQ_LNG;

            while (remaining.length > 0) {{
                let bestIdx = 0, bestDist = Infinity;
                for (let i = 0; i < remaining.length; i++) {{
                    const s = remaining[i][1];
                    const d = Math.sqrt(Math.pow(s.lat - curLat, 2) + Math.pow(s.lng - curLng, 2));
                    if (d < bestDist) {{ bestDist = d; bestIdx = i; }}
                }}
                const [name, data] = remaining.splice(bestIdx, 1)[0];
                sorted.push({{ name, ...data }});
                curLat = data.lat;
                curLng = data.lng;
            }}

            // Build route stops HTML with shopping list per stop
            const stopsDiv = document.getElementById('routeStops');
            stopsDiv.innerHTML = sorted.map((s, i) => {{
                const itemsList = s.items.map(item =>
                    '<li style="font-size:13px; color:#444; padding:2px 0;">' + item + '</li>'
                ).join('');
                return '<div class="route-stop"><span class="stop-num">' + (i+1) + '</span><strong>' + s.name + '</strong>' +
                    '<ul style="margin:6px 0 0 32px; padding-left:16px; list-style:disc;">' + itemsList + '</ul></div>';
            }}).join('');

            // Build Google Maps directions URL
            const waypoints = sorted.map(s => s.lat + ',' + s.lng);
            const mapsUrl = 'https://www.google.com/maps/dir/' + HQ_LAT + ',' + HQ_LNG + '/' + waypoints.join('/');
            document.getElementById('routeLink').href = mapsUrl;

            document.getElementById('routePanel').classList.add('open');
            document.getElementById('routeOverlay').classList.add('open');
        }}

        function closeRoutePanel() {{
            document.getElementById('routePanel').classList.remove('open');
            document.getElementById('routeOverlay').classList.remove('open');
        }}

        let currentRunner = 'I am';

        function pickRunner(who) {{
            currentRunner = who;
            document.getElementById('runnerMe').classList.toggle('active', who === 'I am');
            document.getElementById('runnerOther').classList.toggle('active', who === 'We are');
            document.getElementById('runnerLabel').textContent = who + ' making The Weed Run today';
        }}

        function clearCart() {{
            cart.clear();
            document.querySelectorAll('.deal-item.in-cart').forEach(el => el.classList.remove('in-cart'));
            updateCartUI();
            closeRoutePanel();
        }}

        // Category filtering
        document.querySelectorAll('.filter-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const filter = btn.dataset.filter;

                document.querySelectorAll('.deal-card').forEach(card => {{
                    if (filter === 'all' || card.dataset.category === filter) {{
                        card.classList.remove('hidden');
                    }} else {{
                        card.classList.add('hidden');
                    }}
                }});

                // Hide dispensary sections with no visible deals
                document.querySelectorAll('.dispensary-section').forEach(section => {{
                    const visibleCards = section.querySelectorAll('.deal-card:not(.hidden)');
                    section.style.display = visibleCards.length > 0 ? '' : 'none';
                }});
            }});
        }});
    </script>
</body>
</html>'''

    return html


def main():
    import sys

    print("Fetching deals...")
    raw_deals = fetch_deals()

    print("Parsing deals...")
    deals = parse_deals(raw_deals)
    print(f"Parsed {len(deals)} active deals")

    if not deals:
        print("WARNING: No active deals found!")

    print("Building HTML...")
    now = datetime.now(timezone.utc)
    html = build_html(deals, now)

    OUTPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"Dashboard written to {OUTPUT_FILE}")
    print(f"File size: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")

    if "--push" in sys.argv:
        import subprocess
        print("Pushing to GitHub Pages...")
        subprocess.run(["git", "add", "docs/"], check=True)
        subprocess.run(
            ["git", "commit", "-m", f"update deals {now.strftime('%Y-%m-%d %H:%M')}"],
            check=True,
        )
        subprocess.run(["git", "push"], check=True)
        print("Pushed to GitHub Pages.")


if __name__ == "__main__":
    main()
