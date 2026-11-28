"""Draws the profile's pictures into assets/:

  header-{dark,light}.svg  the squid, "clay" in a pixel font, and a quote
  graph-{dark,light}.svg   the contribution graph, eaten by a squid swimming across
  stats-{dark,light}.svg   stars, contributions, PRs and top languages

Run by .github/workflows/profile.yml every day. Locally: python scripts/build.py
(uses the GitHub CLI when GITHUB_TOKEN isn't set). Standard library only.
"""
import json
import os
import subprocess
import urllib.request
from pathlib import Path

USER = "claykrs"
ASSETS = Path(__file__).resolve().parent.parent / "assets"

# ---- the squid ----

SQUID = [
    "......LO......",
    ".....LOOD.....",
    "....LOOOOD....",
    "...LOOOOOOD...",
    ".DDLOOOOOOODD.",
    "DDDLOOOOOOODDD",
    ".D.LOOOOOOODD.",
    "..LOOOOOOOOD..",
    "..LWKOOOOWKD..",
    "..LKKOOOOKKD..",
    "..LOOOOOOOOD..",
    "...LOOOOOOD...",
    "..O.O.OO.O.O..",
    ".O..O.OO.O..O.",
    ".D.O.O..O.O.D.",
    "...D.D..D.D...",
]
COLORS = {"O": "#FF9A1A", "L": "#FFC46B", "D": "#E2770F", "W": "#FFFFFF", "K": "#1B1B1F"}
EYES = {(8, 3), (8, 4), (9, 3), (9, 4), (8, 9), (8, 10), (9, 9), (9, 10)}

THEMES = {
    "dark": {"text": "#E6EDF3", "muted": "#9198A1", "empty": "#151B23", "line": "#3D444D",
             "levels": ["#151B23", "#5A3410", "#9A520F", "#D9730F", "#FF9A1A"]},
    "light": {"text": "#1F2328", "muted": "#59636E", "empty": "#EFF2F5", "line": "#D1D9E0",
              "levels": ["#EFF2F5", "#FFD9A8", "#FFB45C", "#FF9A1A", "#C76A08"]},
}
FONT = "font-family=\"ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace\""


def squid_rects(ox, oy, s, lids=True):
    body, eyes = [], []
    for y, row in enumerate(SQUID):
        for x, ch in enumerate(row):
            if ch != ".":
                rect = f'<rect x="{ox + x * s}" y="{oy + y * s}" width="{s}" height="{s}" fill="{COLORS[ch]}"/>'
                (eyes if (y, x) in EYES else body).append(rect)
    lid = "".join(f'<rect x="{ox + x * s}" y="{oy + y * s}" width="{s}" height="{s}" fill="{COLORS["O"]}"/>' for (y, x) in sorted(EYES))
    return "".join(body) + "".join(eyes) + (f'<g class="lid">{lid}</g>' if lids else "")


BLINK = (".lid{opacity:0;animation:blink 5s steps(1) infinite}"
         "@keyframes blink{0%,93%,100%{opacity:0}94%,97%{opacity:1}}")

# ---- header ----

LETTERS = {
    "c": [".....", ".....", ".###.", "#....", "#....", "#....", ".###.", ".....", "....."],
    "l": [".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###.", ".....", "....."],
    "a": [".....", ".....", ".###.", "....#", ".####", "#...#", ".####", ".....", "....."],
    "y": [".....", ".....", "#...#", "#...#", "#...#", "#...#", ".####", "....#", ".###."],
}
QUOTE = ["“Soon you will have forgotten all things;", "soon all things will have forgotten you.”"]
BY = "— Marcus Aurelius"


def header(theme):
    t = THEMES[theme]
    p, x0, y0 = 9, 170, 22
    letters = "".join(
        f'<rect x="{x0 + (i * 6 + x) * p}" y="{y0 + y * p}" width="{p}" height="{p}"/>'
        for i, ch in enumerate("clay") for y, row in enumerate(LETTERS[ch]) for x, v in enumerate(row) if v == "#")
    qy = y0 + 9 * p + 30
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="840" height="190" viewBox="0 0 840 190">
<title>clay</title>
<style>.bob{{animation:bob 2.4s steps(1) infinite}}@keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(6px)}}}}{BLINK}@media (prefers-reduced-motion:reduce){{.bob,.lid{{animation:none}}}}</style>
<g class="bob" shape-rendering="crispEdges">{squid_rects(48, 14, 6)}</g>
<g fill="#FF9A1A" shape-rendering="crispEdges">{letters}</g>
<text x="{x0}" y="{qy}" font-size="17" font-style="italic" fill="{t["text"]}" {FONT}>{QUOTE[0]}</text>
<text x="{x0}" y="{qy + 24}" font-size="17" font-style="italic" fill="{t["text"]}" {FONT}>{QUOTE[1]}<tspan font-style="normal" fill="{t["muted"]}">  {BY}</tspan></text>
</svg>
'''

# ---- data ----

QUERY = """{user(login:"%s"){
  contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}
    totalCommitContributions totalPullRequestContributions}
  pullRequests{totalCount}
  repositories(ownerAffiliations:OWNER,isFork:false,first:100,privacy:PUBLIC){nodes{name stargazerCount
    languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}}}}""" % USER


def fetch():
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": QUERY}).encode(),
                                     headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req) as r:
            data = json.load(r)
    else:
        data = json.loads(subprocess.run(["gh", "api", "graphql", "-f", f"query={QUERY}"], capture_output=True, check=True).stdout)
    return data["data"]["user"]

# ---- the graph, eaten ----

LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def graph(theme, user):
    t = THEMES[theme]
    weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]
    cell, gap, top, left = 11, 3, 10, 8
    n = len(weeks)
    width = left * 2 + n * (cell + gap)
    height = top * 2 + 7 * (cell + gap)
    period = 16.0  # seconds for one swim across and back to a full graph
    swim = 0.7  # share of the period spent swimming
    cells = []
    for w, week in enumerate(weeks):
        for day in week["contributionDays"]:
            level = LEVEL.get(day["contributionLevel"], 0)
            y = top + _weekday(day["date"]) * (cell + gap)
            x = left + w * (cell + gap)
            fill = t["levels"][level]
            if level:
                cells.append(f'<rect class="c c{w}" x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{fill}"/>')
            else:
                cells.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{fill}"/>')
    # each column fades to empty as the squid passes it, then everything grows back
    css = [f".c{{animation:eat {period}s linear infinite}}",
           f"@keyframes eat{{0%{{opacity:1}}4%{{opacity:0}}{int((1 - 0.08) * 100)}%{{opacity:0}}100%{{opacity:1}}}}"]
    for w in range(n):
        delay = swim * period * (w + 0.5) / n
        css.append(f".c{w}{{animation-delay:{delay:.2f}s}}")
    s = 2
    sw, sh = len(SQUID[0]) * s, len(SQUID) * s
    sy = top + (7 * (cell + gap) - sh) // 2
    end = width + sw
    css.append(f".sq{{animation:swim {period}s linear infinite}}"
               f"@keyframes swim{{0%{{transform:translateX({-sw}px)}}{int(swim * 100)}%{{transform:translateX({end}px)}}100%{{transform:translateX({end}px)}}}}")
    css.append(BLINK)
    css.append("@media (prefers-reduced-motion:reduce){.c,.sq,.lid{animation:none}.sq{display:none}}")
    total = user["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<title>{total} contributions in the last year, eaten by a squid</title>
<style>{"".join(css)}</style>
{"".join(cells)}
<g class="sq" shape-rendering="crispEdges"><g transform="translate(0 {sy})">{squid_rects(0, 0, s)}</g></g>
</svg>
'''


def _weekday(date):
    import datetime
    return (datetime.date.fromisoformat(date).weekday() + 1) % 7  # Sunday first, like GitHub

# ---- stats ----


def stats(theme, user):
    t = THEMES[theme]
    repos = user["repositories"]["nodes"]
    stars = sum(r["stargazerCount"] for r in repos)
    cc = user["contributionsCollection"]
    langs = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            name = e["node"]["name"]
            langs.setdefault(name, [0, e["node"]["color"] or "#8B949E"])[0] += e["size"]
    every = sum(v[0] for v in langs.values()) or 1
    top = [kv for kv in sorted(langs.items(), key=lambda kv: -kv[1][0])[:5] if kv[1][0] / every >= 0.01]
    total = sum(v[0] for _, v in top) or 1
    items = [("contributions this year", cc["contributionCalendar"]["totalContributions"]),
             ("commits", cc["totalCommitContributions"]),
             ("pull requests", user["pullRequests"]["totalCount"]),
             ("stars", stars)]
    w = 840
    col = (w - 40) // len(items)
    nums = "".join(
        f'<text x="{20 + i * col}" y="44" font-size="26" font-weight="700" fill="#FF9A1A" {FONT}>{v}</text>'
        f'<text x="{20 + i * col}" y="66" font-size="13" fill="{t["muted"]}" {FONT}>{label}</text>'
        for i, (label, v) in enumerate(items))
    bar, x = [], 20
    span = w - 40
    for name, (size, color) in top:
        bw = span * size / total
        bar.append(f'<rect x="{x:.1f}" y="92" width="{max(bw - 2, 1):.1f}" height="8" rx="2" fill="{color}"/>')
        x += bw
    legend, lx = [], 20
    for name, (size, color) in top:
        label = f"{name} {100 * size / total:.0f}%"
        legend.append(f'<rect x="{lx}" y="114" width="9" height="9" rx="2" fill="{color}"/>'
                      f'<text x="{lx + 14}" y="123" font-size="12" fill="{t["text"]}" {FONT}>{label}</text>')
        lx += 14 + len(label) * 7.6 + 22
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="140" viewBox="0 0 {w} 140">
<title>GitHub stats for {USER}</title>
<rect x="0.5" y="0.5" width="{w - 1}" height="139" rx="8" fill="none" stroke="{t["line"]}"/>
{nums}{"".join(bar)}{"".join(legend)}
</svg>
'''


def main():
    ASSETS.mkdir(exist_ok=True)
    user = fetch()
    for theme in THEMES:
        (ASSETS / f"header-{theme}.svg").write_text(header(theme), encoding="utf8")
        (ASSETS / f"graph-{theme}.svg").write_text(graph(theme, user), encoding="utf8")
        (ASSETS / f"stats-{theme}.svg").write_text(stats(theme, user), encoding="utf8")


if __name__ == "__main__":
    main()
