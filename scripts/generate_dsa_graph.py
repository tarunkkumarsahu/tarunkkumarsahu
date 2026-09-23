"""Build daily commit charts for all public owned repos and Structured-DSA.

Counts only commits authored by the GitHub user on each repository's default
branch. Dates are UTC. The default GitHub Actions token cannot read private
repositories owned by another installation.
"""

import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USERNAME = "tarunkkumarsahu"
DSA_REPO = "Structured-DSA"
DAYS = 30
TODAY = datetime.now(timezone.utc).date()
DATES = [TODAY - timedelta(days=i) for i in range(DAYS - 1, -1, -1)]
DATE_KEYS = {d.isoformat() for d in DATES}
SINCE = f"{DATES[0].isoformat()}T00:00:00Z"
UNTIL = f"{(TODAY + timedelta(days=1)).isoformat()}T00:00:00Z"


def github_json(path, params):
    url = "https://api.github.com" + path + "?" + urlencode(params)
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "tarun-commit-graphs",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def public_repositories():
    page = 1
    while True:
        repositories = github_json(
            f"/users/{USERNAME}/repos",
            {"type": "owner", "per_page": 100, "page": page},
        )
        for repository in repositories:
            if not repository.get("private"):
                yield repository["name"]
        if len(repositories) < 100:
            return
        page += 1


def repository_commits(repository_name):
    page = 1
    while True:
        try:
            commits = github_json(
                f"/repos/{USERNAME}/{repository_name}/commits",
                {
                    "author": USERNAME,
                    "since": SINCE,
                    "until": UNTIL,
                    "per_page": 100,
                    "page": page,
                },
            )
        except HTTPError as error:
            if error.code in (404, 409):
                # A repo may be empty, or removed between enumeration and lookup.
                print(f"Skipping {repository_name}: HTTP {error.code}")
                return
            raise

        for item in commits:
            # Group by UTC committer date, the date represented by a commit.
            day = item["commit"]["committer"]["date"][:10]
            if day in DATE_KEYS:
                yield day
        if len(commits) < 100:
            return
        page += 1


def chart(title, counts, output):
    values = [counts[day.isoformat()] for day in DATES]
    width, height = 900, 280
    left, right, top, bottom = 48, 24, 65, 55
    chart_width = width - left - right
    chart_height = height - top - bottom
    maximum = max(max(values), 1)

    def x_pos(index):
        return left + index * chart_width / (DAYS - 1)

    def y_pos(value):
        return top + chart_height - value / maximum * chart_height

    points = " ".join(
        f"{x_pos(i):.1f},{y_pos(value):.1f}"
        for i, value in enumerate(values)
    )
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" rx="16" fill="#020617"/>',
        f'<text x="48" y="32" fill="#00E5FF" font-family="monospace" '
        f'font-size="17" font-weight="bold">{title}</text>',
        f'<text x="852" y="32" fill="#67E8F9" text-anchor="end" '
        f'font-family="monospace" font-size="12">30D TOTAL: {sum(values)}</text>',
    ]
    for fraction in (0, 0.5, 1):
        y = y_pos(maximum * fraction)
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
            f'<circle cx="{x_pos(i):.1f}" cy="{y_pos(value):.1f}" '
            'r="3.5" fill="#00E5FF"/>'
        )
    for i in range(0, DAYS, 5):
        svg.append(
            f'<text x="{x_pos(i):.1f}" y="{height-22}" '
            'text-anchor="middle" fill="#94A3B8" '
            f'font-family="monospace" font-size="11">'
            f'{DATES[i].strftime("%d %b")}</text>'
        )
    svg.extend([
        '<text x="48" y="269" fill="#64748B" font-family="monospace" '
        'font-size="10">Public owned repos; authored commits; UTC dates</text>',
        '</svg>',
    ])
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(svg) + "\n", encoding="utf-8")
    print(f"Updated {destination}: {sum(values)} commits over {DAYS} days")


all_counts = Counter()
dsa_counts = Counter()
repo_count = 0
for repository in public_repositories():
    repo_count += 1
    for day in repository_commits(repository):
        all_counts[day] += 1
        if repository == DSA_REPO:
            dsa_counts[day] += 1

print(f"Counted {repo_count} public owned repositories")
chart("ALL REPOSITORIES // DAILY COMMITS", all_counts, "assets/all-repos-commits.svg")
chart("STRUCTURED-DSA // DAILY COMMITS", dsa_counts, "assets/dsa-commits.svg")
