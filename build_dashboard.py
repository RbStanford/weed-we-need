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


def get_locations_html(chain_key):
    """Build HTML for nearby locations with distances and Google Maps links."""
    locations = NEARBY_LOCATIONS.get(chain_key, [])
    if not locations:
        return ""

    # Sort by distance from Jared
    locs_with_dist = []
    for name, addr, city, lat, lng in locations:
        dist = haversine(JARED_LAT, JARED_LNG, lat, lng)
        maps_url = f"https://www.google.com/maps/dir/{JARED_LAT},{JARED_LNG}/{lat},{lng}"
        locs_with_dist.append((dist, name, addr, city, maps_url))
    locs_with_dist.sort()

    links = []
    for dist, name, addr, city, maps_url in locs_with_dist:
        links.append(
            f'<a href="{maps_url}" target="_blank" rel="noopener" class="location-link">'
            f'<span class="loc-distance">{dist:.1f} mi</span> '
            f'<span class="loc-addr">{addr}, {city}</span>'
            f'<span class="loc-arrow">&#8599;</span>'
            f'</a>'
        )

    return f'<div class="locations">{"".join(links)}</div>'


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

            desc_html = ""
            if deal["description"]:
                desc_lines = deal["description"].replace("\n", "<br>")
                desc_html = f'<p class="deal-desc">{desc_lines}</p>'

            cards_html.append(f'''
            <div class="deal-card" data-category="{deal['category_name'].lower()}">
                {img_html}
                <div class="deal-content">
                    <div class="deal-header">
                        <span class="category-tag" style="background:{deal['category_color']}20; color:{deal['category_color']}">{deal['category_name']}</span>
                        {badge}
                        {verified}
                    </div>
                    <h3 class="deal-title">{deal['title']}</h3>
                    {desc_html}
                </div>
            </div>''')

        website_link = ""
        if disp["website"]:
            website_link = f'<a href="{disp["website"]}" target="_blank" rel="noopener" class="disp-link">Visit Site &rarr;</a>'

        standing_deals = ""
        if disp["description"]:
            standing_deals = f'<p class="disp-standing">{disp["description"]}</p>'

        # Get nearby locations with distances and directions links
        chain_key = disp_name.lower().strip()
        locations_html = get_locations_html(chain_key)

        dispensary_sections.append(f'''
        <section class="dispensary-section" data-dispensary="{disp_name.lower()}">
            <div class="disp-header">
                <div class="disp-info">
                    <img src="{disp['logo']}" alt="" class="disp-logo" onerror="this.style.display='none'">
                    <div>
                        <h2 class="disp-name">{disp_name}</h2>
                        {standing_deals}
                    </div>
                </div>
                {website_link}
            </div>
            {locations_html}
            <div class="deals-grid">
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

        .locations {{
            display: flex;
            flex-direction: column;
            gap: 4px;
            margin-bottom: 12px;
        }}

        .location-link {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            text-decoration: none;
            color: var(--text);
            font-size: 13px;
        }}

        .location-link:active {{
            background: var(--accent-dim);
        }}

        .loc-distance {{
            font-weight: 700;
            color: var(--accent);
            min-width: 50px;
        }}

        .loc-addr {{
            flex: 1;
            color: var(--text-muted);
        }}

        .loc-arrow {{
            color: var(--accent);
            font-size: 16px;
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
            max-height: 180px;
            object-fit: cover;
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

        /* Light mode only */
    </style>
</head>
<body>
    <header class="header">
        <div class="header-top">
            <div>
                <h1>&#127807; The Weed We Need</h1>
                <p class="stats">Jared &amp; Nicole's Daily Deal Report &middot; {deal_count} deals &middot; {dispensary_count} dispensaries</p>
                <p class="stats">Updated {timestamp}</p>
            </div>
            <button class="refresh-btn" onclick="location.reload()">&#8635; Refresh</button>
        </div>
        <div class="filters">
            {"".join(filter_buttons)}
        </div>
    </header>

    <main class="main" id="deals-container">
        <section class="hq-section">
            <h2 class="hq-title">&#128205; YOU ARE HERE</h2>
            <p class="hq-subtitle">All distances measured from HQ</p>
            <div class="hq-photo">
                <img src="jared-hq.png" alt="Jared and Nicole's HQ">
                <div class="hq-badge">&#127807; HQ &middot; 4665 S 25th St</div>
            </div>
        </section>

        {"".join(dispensary_sections)}
    </main>

    <footer class="footer">
        <p>Data from <a href="https://cannadealsfl.com" target="_blank">CannaDealsFL</a></p>
        <p>Made with &#10084;&#65039; by Rob</p>
    </footer>

    <script>
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
