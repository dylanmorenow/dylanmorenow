"""
Generate dark_mode.svg & light_mode.svg (neofetch-style GitHub profile README).
Edit the CONFIG section, then run:  python generate.py
"""
from datetime import datetime, timedelta, timezone
import calendar
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

# Filled in automatically in Step 5 (GitHub Actions). Placeholders for now.
STATS = {
    "repos": "-", "contributed": "-", "stars": "-",
    "commits": "-", "followers": "-",
    "loc": "-", "loc_add": "-", "loc_del": "-",
}

WIDTH      = 60    # characters per line in the right column
FONT_SIZE  = 16
LINE_H     = 20
CHAR_W     = FONT_SIZE * 0.63  # safe monospace width estimate (covers wider fallback fonts)

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


RAMP = " .:-=+*#%@"


def invert_ascii(line):
    # light background: dense chars look dark, so flip the ramp (keep spaces as background)
    n = len(RAMP)
    return "".join(RAMP[n - RAMP.index(ch)] if ch in RAMP and ch != " " else ch for ch in line)


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
    rows = max(len(ascii_lines), len(info_lines))
    width = int(x_info + WIDTH * CHAR_W + pad)
    height = int(rows * LINE_H + pad * 2)
    y0 = pad + LINE_H - 4

    out = [f'<?xml version="1.0" encoding="UTF-8"?>',
           f'<svg xmlns="http://www.w3.org/2000/svg" font-family="Consolas, Menlo, \'Courier New\', monospace" '
           f'width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-size="{FONT_SIZE}px">',
           "<style>",
           f".text{{fill:{c['text']}}} .key{{fill:{c['key']}}} .value{{fill:{c['value']}}} "
           f".dots{{fill:{c['dots']}}} .add{{fill:{c['add']}}} .dele{{fill:{c['dele']}}} "
           f"text, tspan{{white-space:pre}}",
           "</style>",
           f'<rect width="{width}" height="{height}" fill="{c["bg"]}" rx="15"/>',
           f'<text x="{x_ascii}" y="{y0}" fill="{c["ascii"]}" xml:space="preserve">']
    for i, l in enumerate(ascii_lines):
        out.append(f'<tspan x="{x_ascii}" y="{y0 + i*LINE_H}">{escape(l)}</tspan>')
    out.append("</text>")
    out.append(f'<text x="{x_info}" y="{y0}" class="text" xml:space="preserve">')
    for i, segs in enumerate(info_lines):
        inner = "".join(f'<tspan class="{cls}">{escape(t)}</tspan>' for t, cls in segs)
        out.append(f'<tspan x="{x_info:.1f}" y="{y0 + i*LINE_H}">{inner}</tspan>')
    out.append("</text></svg>")
    with open(f"{theme}_mode.svg", "w", encoding="utf-8") as f:
        f.write("\n".join(out))


if __name__ == "__main__":
    for t in THEMES:
        render(t)
    print("Generated dark_mode.svg & light_mode.svg | Uptime:", uptime())
