"""Generate a 30-day commit-count SVG for the public Structured-DSA repository."""
import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USERNAME = "tarunkkumarsahu"
REPOSITORY = "Structured-DSA"
DAYS = 30
TODAY = datetime.now(timezone.utc).date()
DATES = [TODAY - timedelta(days=n) for n in range(DAYS - 1, -1, -1)]
COUNTS = Counter()

page = 1
while True:
    query = urlencode({
        "author": USERNAME,
        "since": f"{DATES[0].isoformat()}T00:00:00Z",
        "per_page": 100,
        "page": page,
    })
    url = f"https://api.github.com/repos/{USERNAME}/{REPOSITORY}/commits?{query}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "structured-dsa-commit-graph",
    }
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        commits = json.load(response)
    if not commits:
        break
    for commit in commits:
        day = commit["commit"]["author"]["date"][:10]
        if day in {d.isoformat() for d in DATES}:
            COUNTS[day] += 1
    if len(commits) < 100:
        break
    page += 1

values = [COUNTS[day.isoformat()] for day in DATES]
width, height = 900, 280
left, right, top, bottom = 48, 24, 65, 55
chart_width = width - left - right
chart_height = height - top - bottom
maximum = max(max(values), 1)

def x_coord(index):
    return left + index * chart_width / (DAYS - 1)

def y_coord(value):
    return top + chart_height - value / maximum * chart_height

points = " ".join(
    f"{x_coord(i):.1f},{y_coord(value):.1f}"
    for i, value in enumerate(values)
)
svg = [
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
    '<rect width="100%" height="100%" rx="16" fill="#020617"/>',
    '<text x="48" y="32" fill="#00E5FF" font-family="monospace" '
    'font-size="17" font-weight="bold">STRUCTURED-DSA // DAILY COMMITS</text>',
    f'<text x="852" y="32" fill="#67E8F9" text-anchor="end" '
    f'font-family="monospace" font-size="12">30D TOTAL: {sum(values)}</text>',
]
for fraction in (0, 0.5, 1):
    y = y_coord(maximum * fraction)
    svg.append(
        f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" '
        'stroke="#173047" stroke-dasharray="4 5"/>'
    )
    svg.append(
        f'<text x="36" y="{y+4:.1f}" text-anchor="end" '
        f'fill="#67E8F9" font-size="11">{round(maximum*fraction)}</text>'
    )
svg.append(
    f'<polyline points="{points}" fill="none" stroke="#00E5FF" '
    'stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>'
)
for i, value in enumerate(values):
    svg.append(
        f'<circle cx="{x_coord(i):.1f}" cy="{y_coord(value):.1f}" r="3.5" '
        'fill="#00E5FF"/>'
    )
for i in range(0, DAYS, 5):
    svg.append(
        f'<text x="{x_coord(i):.1f}" y="{height-22}" text-anchor="middle" '
        'fill="#94A3B8" font-family="monospace" font-size="11">'
        f'{DATES[i].strftime("%d %b")}</text>'
    )
svg.extend([
    '<text x="48" y="269" fill="#64748B" font-family="monospace" '
    'font-size="10">Public repository; authored commits; UTC dates</text>',
    '</svg>',
])

destination = Path("assets/dsa-commits.svg")
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text("\n".join(svg) + "\n", encoding="utf-8")
print(f"Generated {destination}: {sum(values)} commits in the past {DAYS} UTC days")
