#!/usr/bin/env python3
"""Render a GitHub contribution activity graph using the authenticated GitHub GraphQL API."""
import datetime as dt
import html
import json
import math
import os
from pathlib import Path
import urllib.request

USER = os.environ.get("GH_USERNAME", "imranarshad3")
TOKEN = os.environ["GH_TOKEN"]
OUT = Path("assets/activity-graph.svg")
QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

def fetch():
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={
            "Authorization": "Bearer " + TOKEN,
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "self-hosted-readme-chart"
        },
        method="POST"
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    if data.get("errors"):
        raise RuntimeError(json.dumps(data["errors"]))
    user = data.get("data", {}).get("user")
    if not user:
        raise RuntimeError("GitHub profile not found: " + USER)
    weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"][-52:]
    if not weeks:
        raise RuntimeError("No contribution calendar data returned")
    return weeks

def render(weeks):
    total_by_week = [sum(int(d["contributionCount"]) for d in w["contributionDays"]) for w in weeks]
    n = len(weeks)
    active_days = sum(1 for w in weeks for d in w["contributionDays"] if d["contributionCount"] > 0)
    total = sum(total_by_week)
    y_max = max(4, math.ceil(max(total_by_week) / 4) * 4)
    left, right, top, bottom = 93, 1305, 136, 308
    points = [(left + i * (right-left) / max(1, n-1), bottom - v * (bottom-top) / y_max)
              for i,v in enumerate(total_by_week)]
    series = " ".join(f"{x:.1f},{y:.1f}" for x,y in points)
    area = f"M{left},{bottom} L" + " L".join(f"{x:.1f},{y:.1f}" for x,y in points) + f" L{right},{bottom}Z"
    grid=[]
    for i in range(5):
        y=top+(bottom-top)*i/4
        grid.append(f'<path d="M{left} {y:.1f}H{right}" stroke="#41606A" opacity=".55" stroke-dasharray="4 9"/>')
        grid.append(f'<text x="75" y="{y+5:.1f}" text-anchor="end" font-size="13" fill="#93ADB8">{round(y_max*(4-i)/4)}</text>')
    for i in sorted(set([0,13,26,39,n-1])):
        if i >= n:
            continue
        date = weeks[i]["contributionDays"][0]["date"]
        label = dt.date.fromisoformat(date).strftime("%b %Y")
        grid.append(f'<text x="{points[i][0]:.1f}" y="340" text-anchor="middle" font-size="14" fill="#A9BBC5">{html.escape(label)}</text>')
    dots = ''.join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#8DEBD3" stroke="#142532" stroke-width="2"/>'
                   for x,y in points if y < bottom-0.2)
    refreshed = dt.datetime.now(dt.timezone.utc).strftime("%d %b %Y %H:%M UTC")
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="392" viewBox="0 0 1400 392" role="img" aria-label="GitHub activity: {total} contributions across {n} weeks">
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#101F2B"/><stop offset=".6" stop-color="#142B36"/><stop offset="1" stop-color="#101E2A"/></linearGradient>
<linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#8DEBD3" stop-opacity=".44"/><stop offset="1" stop-color="#8DEBD3" stop-opacity=".02"/></linearGradient>
<linearGradient id="line"><stop stop-color="#7DE6C9"/><stop offset="1" stop-color="#B6A6F9"/></linearGradient></defs>
<rect width="1400" height="392" rx="19" fill="url(#bg)"/><rect x="1" y="1" width="1398" height="390" rx="18" fill="none" stroke="#34525D" stroke-width="2"/>
<g font-family="Arial,Helvetica,sans-serif">
<text x="42" y="50" font-size="29" fill="#EFF9F5" font-weight="bold">Contribution velocity</text>
<text x="43" y="78" font-size="15" fill="#AAC1C9">Verified GitHub activity across the last 52 weeks</text>
<text x="1030" y="43" font-size="14" fill="#8DEBD3">CONTRIBUTIONS</text>
<text x="1030" y="76" font-size="30" font-weight="bold" fill="#EFF9F5">{total:,}</text>
<text x="1255" y="43" font-size="14" fill="#A6BFC7">ACTIVE DAYS</text>
<text x="1255" y="76" font-size="30" font-weight="bold" fill="#EFF9F5">{active_days}</text>
{''.join(grid)}
<path d="{area}" fill="url(#area)"/>
<polyline points="{series}" fill="none" stroke="url(#line)" stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round"/>
{dots}
<path d="M42 358H1355" stroke="#34525D"/>
<circle cx="53" cy="376" r="5" fill="#8DEBD3"/>
<text x="68" y="381" font-size="12.5" fill="#9FBDC4">Real GitHub contribution counts · Refreshed {html.escape(refreshed)}</text>
</g></svg>'''
    return svg

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(fetch()), encoding="utf-8")
    print("Updated " + str(OUT))
