"""
Generate dark_mode.svg & light_mode.svg (neofetch-style GitHub profile README).
Edit the CONFIG section, then run:  python generate.py
"""
from datetime import datetime, timedelta, timezone
import calendar
import json
import os
import urllib.request
from xml.sax.saxutils import escape

# ============================ CONFIG ============================
USERNAME   = "dylanmorenow"
BIRTHDAY   = (2007, 9, 27)          # (year, month, day) -> "Uptime"
TIMEZONE   = timezone(timedelta(hours=7))   # WIB (Jakarta)

INFO = [
    ("OS", "Windows, Kali Linux"),
    ("Uptime", None),               # auto-filled
    ("Host", "Gapaian"),
    ("Kernel", "Software Engineer"),
    ("IDE", "Claude Code, Cursor, VS Code"),
    None,
    ("Languages.Programming", "Python, C, C++, Java, TypeScript"),
    ("Languages.Real", "Indonesian, English"),
    ("Hobbies", "Arguing with Claude"),
]
EXPERIENCE = [
    ("Previously", "AI Product Manager @ Gapaian"),
]
CONTACT = [
    ("Email", "dylanmoreno927@gmail.com"),
    ("LinkedIn", "in/dylanmorenoz"),
]

INCLUDE_PRIVATE = True   # count private repos too (needs token with "repo" scope)

# Placeholders, used when no ACCESS_TOKEN is set (e.g. running locally)
STATS = {
    "repos": "-", "contributed": "-", "stars": "-",
    "commits": "-", "followers": "-",
    "loc": "-", "loc_add": "-", "loc_del": "-",
}

WIDTH      = 60    # characters per line in the right column
FONT_SIZE  = 16
LINE_H     = 20
CHAR_W     = FONT_SIZE * 0.63  # safe monospace width estimate (covers wider fallback fonts)

# Animation (plays once when the page loads, then only the cursor blinks)
ANIMATE    = True
ASCII_STEP = 0.06   # seconds between ASCII rows
TYPE_STEP  = 0.12   # seconds between info lines
LOOP_TEXT  = "Hello World!"   # typed + backspaced forever after the prompt (set "" to disable)

THEMES = {
    "dark":  dict(bg="#161b22", text="#c9d1d9", key="#ffa657", value="#a5d6ff",
                  dots="#616e7f", ascii="#c9d1d9", add="#3fb950", dele="#f85149"),
    "light": dict(bg="#f6f8fa", text="#24292f", key="#953800", value="#0a3069",
                  dots="#c2cfde", ascii="#24292f", add="#1a7f37", dele="#cf222e"),
}
# ================================================================


def uptime():
    today = datetime.now(TIMEZONE).date()
    by, bm, bd = BIRTHDAY
    y, m, d = today.year - by, today.month - bm, today.day - bd
    if d < 0:
        m -= 1
        pm = today.month - 1 or 12
        py = today.year if today.month != 1 else today.year - 1
        d += calendar.monthrange(py, pm)[1]
    if m < 0:
        y -= 1
        m += 12
    p = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"
    s = f"{p(y,'year')}, {p(m,'month')}, {p(d,'day')}"
    return s + (" 🎂" if (m, d) == (0, 0) else "")


# A line is a list of (text, css_class) segments
def kv(key, value_segs, width):
    if isinstance(value_segs, str):
        value_segs = [(value_segs, "value")]
    head = f". {key}:"
    vlen = sum(len(t) for t, _ in value_segs)
    ndots = max(1, width - len(head) - vlen - 2)
    return [(". ", "text"), (f"{key}:", "key"), (" " + "." * ndots + " ", "dots")] + value_segs


def header(title, width, first=False):
    if first:
        t = f"{USERNAME}@github "
        return [(t, "value"), ("─" * (width - len(t)), "text")]
    t = f"─ {title} "
    return [("─ ", "text"), (title, "value"), (" " + "─" * (width - len(t)), "text")]


def two_col(k1, v1, k2, v2, width):
    left_w = 30
    right_w = width - left_w - 3 + 2   # +2: the '. ' prefix is dropped below
    return kv(k1, v1, left_w) + [(" | ", "text")] + kv(k2, v2, right_w)[1:]


def build_lines():
    W = WIDTH
    lines = [header(None, W, first=True)]
    for item in INFO:
        if item is None:
            lines.append([])
            continue
        k, v = item
        lines.append(kv(k, uptime() if k == "Uptime" else v, W))
    lines += [[], header("Experience", W)] + [kv(k, v, W) for k, v in EXPERIENCE]
    lines += [[], header("Contact", W)] + [kv(k, v, W) for k, v in CONTACT]
    s = STATS
    lines += [[], header("GitHub Stats", W),
        two_col("Repos", [(str(s["repos"]), "value"), (" {Contributed: ", "text"),
                          (str(s["contributed"]), "value"), ("}", "text")],
                "Stars", str(s["stars"]), W),
        two_col("Commits", str(s["commits"]), "Followers", str(s["followers"]), W),
        kv("Lines of Code", [(str(s["loc"]), "value"), (" ( ", "text"),
                             (f"{s['loc_add']}++", "add"), (", ", "text"),
                             (f"{s['loc_del']}--", "dele"), (" )", "text")], W),
    ]
    return lines


# ======================= GITHUB STATS =======================
API = "https://api.github.com/graphql"


def gql(query, variables, token):
    req = urllib.request.Request(
        API, data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.load(r)
    if res.get("errors") and not res.get("data"):
        raise RuntimeError(res["errors"])
    return res["data"]


def list_repos(token, affiliations):
    privacy = "" if INCLUDE_PRIVATE else ", privacy: PUBLIC"
    q = """query($login:String!, $cursor:String) { user(login:$login) {
      repositories(first:100, after:$cursor, ownerAffiliations:[%s]%s) {
        totalCount pageInfo { hasNextPage endCursor }
        nodes { name owner { login } stargazerCount } } } }""" % (",".join(affiliations), privacy)
    repos, cursor = [], None
    while True:
        d = gql(q, {"login": USERNAME, "cursor": cursor}, token)["user"]["repositories"]
        repos += d["nodes"]
        if not d["pageInfo"]["hasNextPage"]:
            return repos
        cursor = d["pageInfo"]["endCursor"]


def repo_loc(token, owner, name, user_id):
    q = """query($owner:String!, $name:String!, $cursor:String, $id:ID!) {
      repository(owner:$owner, name:$name) { defaultBranchRef { target { ... on Commit {
        history(first:100, after:$cursor, author:{id:$id}) {
          pageInfo { hasNextPage endCursor } nodes { additions deletions } } } } } } }"""
    add = dele = 0
    cursor = None
    while True:
        repo = gql(q, {"owner": owner, "name": name, "cursor": cursor, "id": user_id}, token)["repository"]
        if not repo or not repo["defaultBranchRef"]:
            return 0, 0          # empty repo
        h = repo["defaultBranchRef"]["target"]["history"]
        for n in h["nodes"]:
            add += n["additions"]
            dele += n["deletions"]
        if not h["pageInfo"]["hasNextPage"]:
            return add, dele
        cursor = h["pageInfo"]["endCursor"]


def fetch_stats(token):
    info = gql("""query($login:String!) { user(login:$login) {
        id createdAt followers { totalCount }
        repositoriesContributedTo(first:1, includeUserRepositories:false,
          contributionTypes:[COMMIT, PULL_REQUEST]) { totalCount } } }""",
        {"login": USERNAME}, token)["user"]

    owned = list_repos(token, ["OWNER"])
    stars = sum(r["stargazerCount"] for r in owned)

    # Commits: sum contribution calendar year by year since the account was created
    commits = 0
    start = datetime.fromisoformat(info["createdAt"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    while start < now:
        end = min(start + timedelta(days=365), now)
        commits += gql("""query($login:String!, $from:DateTime!, $to:DateTime!) { user(login:$login) {
            contributionsCollection(from:$from, to:$to) { totalCommitContributions } } }""",
            {"login": USERNAME, "from": start.isoformat(), "to": end.isoformat()},
            token)["user"]["contributionsCollection"]["totalCommitContributions"]
        start = end

    # Lines of code: your own commits in every repo you own / collaborate on / are an org member of
    add = dele = 0
    for r in list_repos(token, ["OWNER", "COLLABORATOR", "ORGANIZATION_MEMBER"]):
        try:
            a, d = repo_loc(token, r["owner"]["login"], r["name"], info["id"])
            add, dele = add + a, dele + d
        except Exception as e:
            print(f"  skip {r['owner']['login']}/{r['name']}: {e}")

    f = lambda n: f"{n:,}"
    return {
        "repos": f(len(owned)), "contributed": f(info["repositoriesContributedTo"]["totalCount"]),
        "stars": f(stars), "commits": f(commits), "followers": f(info["followers"]["totalCount"]),
        "loc": f(add - dele), "loc_add": f(add), "loc_del": f(dele),
    }


# ========================= RENDERING =========================
RAMP = " .:-=+*#%@"


def invert_ascii(line):
    # light background: dense chars look dark, so flip the ramp (keep spaces as background)
    n = len(RAMP)
    return "".join(RAMP[n - RAMP.index(ch)] if ch in RAMP and ch != " " else ch for ch in line)


def typing_loop(prompt, x, y, start, c):
    """Frame-based typing loop: one <text> per state, so the cursor always sits exactly
    after the last character, whatever font the viewer has."""
    text = LOOP_TEXT
    if not text:
        return "", [f'<text class="t" x="{x:.1f}" y="{y}" xml:space="preserve">'
                    f'<tspan class="add">{escape(prompt)}</tspan></text>']
    seq = []                                   # (chars shown, cursor on, duration)
    for k in range(len(text) + 1):
        seq.append((k, True, 0.10))            # typing
    for i in range(4):
        seq.append((len(text), i % 2 == 1, 0.5))   # hold + blink
    for k in range(len(text) - 1, -1, -1):
        seq.append((k, True, 0.06))            # backspace
    for i in range(2):
        seq.append((0, i % 2 == 1, 0.5))       # empty + blink
    total = sum(d for *_, d in seq)

    spans, t = {}, 0.0
    for k, cur, d in seq:
        spans.setdefault((k, cur), []).append((t / total * 100, (t + d) / total * 100))
        t += d

    css, els, pad = [], [], " " * len(prompt)
    for n, ((k, cur), ivs) in enumerate(sorted(spans.items())):
        kf = ["0%{opacity:0}"] if ivs[0][0] > 0 else []
        for a, b in ivs:
            kf.append(f"{a:.3f}%{{opacity:1}}")
            if b < 99.999:
                kf.append(f"{b:.3f}%{{opacity:0}}")
        if ivs[-1][1] < 99.999:
            kf.append("100%{opacity:0}")
        css.append(f"@keyframes lp{n}{{{''.join(kf)}}}"
                   f".lp{n}{{opacity:0;animation:lp{n} {total:.2f}s step-end {start:.2f}s infinite}}")
        final = " final" if (k == len(text) and not cur) else ""
        els.append(f'<text class="lp{n}{final}" x="{x:.1f}" y="{y}" xml:space="preserve">'
                   f'{pad}<tspan class="value">{escape(text[:k])}</tspan>'
                   f'<tspan class="text">{"█" if cur else ""}</tspan></text>')
    css.append("@media (prefers-reduced-motion:reduce){[class^=lp]{animation:none!important}.final{opacity:1!important}}")
    prompt_el = (f'<text class="t" x="{x:.1f}" y="{y}" xml:space="preserve" '
                 f'style="animation-delay:{start - 0.5:.2f}s"><tspan class="add">{escape(prompt)}</tspan></text>')
    return "".join(css), [prompt_el] + els


def render(theme):
    c = THEMES[theme]
    ascii_lines = open("ascii.txt", encoding="utf-8").read().rstrip("\n").split("\n")
    if theme == "light":
        ascii_lines = [invert_ascii(l) for l in ascii_lines]
    info_lines = build_lines()
    ascii_w = max(len(l) for l in ascii_lines)
    pad = 20
    x_ascii = pad
    x_info = pad + ascii_w * CHAR_W + 30
    rows = max(len(ascii_lines), len(info_lines)) + (2 if ANIMATE else 0)   # +prompt line
    width = int(x_info + WIDTH * CHAR_W + pad)
    height = int(rows * LINE_H + pad * 2)
    y0 = pad + LINE_H - 4

    anim_css = ""
    if ANIMATE:
        anim_css = (
            ".a{opacity:0;animation:fade .45s ease-out forwards}"
            ".t{opacity:0;clip-path:inset(0 100% 0 0);animation:type .45s steps(30,end) forwards}"
            ".cur{opacity:0;animation:show 0s forwards,blink 1.1s step-end infinite}"
            "@keyframes fade{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:none}}"
            "@keyframes type{0%{opacity:1;clip-path:inset(0 100% 0 0)}100%{opacity:1;clip-path:inset(0 0 0 0)}}"
            "@keyframes show{to{opacity:1}}"
            "@keyframes blink{0%{opacity:1}50%{opacity:0}}"
            "@media (prefers-reduced-motion:reduce){.a,.t,.cur{animation:none;opacity:1;clip-path:none}}"
        )

    def delay(sec):
        return f' style="animation-delay:{sec:.2f}s"' if ANIMATE else ""

    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<svg xmlns="http://www.w3.org/2000/svg" font-family="Consolas, Menlo, \'Courier New\', monospace" '
           f'width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-size="{FONT_SIZE}px">',
           "<style>",
           f".text{{fill:{c['text']}}} .key{{fill:{c['key']}}} .value{{fill:{c['value']}}} "
           f".dots{{fill:{c['dots']}}} .add{{fill:{c['add']}}} .dele{{fill:{c['dele']}}} "
           f"text, tspan{{white-space:pre}}" + anim_css,
           "</style>",
           f'<rect width="{width}" height="{height}" fill="{c["bg"]}" rx="15"/>']

    # 1) ASCII portrait fades in from top to bottom
    for i, l in enumerate(ascii_lines):
        out.append(f'<text class="a" x="{x_ascii}" y="{y0 + i*LINE_H}" fill="{c["ascii"]}" '
                   f'xml:space="preserve"{delay(i * ASCII_STEP)}>{escape(l)}</text>')

    # 2) Info lines get "typed" one after another
    t0 = len(ascii_lines) * ASCII_STEP * 0.6
    for i, segs in enumerate(info_lines):
        if not segs:
            continue
        inner = "".join(f'<tspan class="{cls}">{escape(t)}</tspan>' for t, cls in segs)
        out.append(f'<text class="t text" x="{x_info:.1f}" y="{y0 + i*LINE_H}" '
                   f'xml:space="preserve"{delay(t0 + i * TYPE_STEP)}>{inner}</text>')

    # 3) Shell prompt with a looping typing effect
    if ANIMATE:
        y = y0 + (rows - 1) * LINE_H
        t_end = t0 + len(info_lines) * TYPE_STEP + 0.3
        prompt = f"{USERNAME}@github:~$ "
        css, els = typing_loop(prompt, x_info, y, t_end + 0.5, c)
        out[3] = out[3] + css                       # append keyframes to the <style> block
        out += els

    out.append("</svg>")
    with open(f"{theme}_mode.svg", "w", encoding="utf-8") as f:
        f.write("\n".join(out))


if __name__ == "__main__":
    token = os.environ.get("ACCESS_TOKEN")
    if token:
        STATS.update(fetch_stats(token))
        print("Stats:", STATS)
    else:
        print("No ACCESS_TOKEN set -> using placeholder stats")
    for t in THEMES:
        render(t)
    print("Generated dark_mode.svg & light_mode.svg | Uptime:", uptime())
