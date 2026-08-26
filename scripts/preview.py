#!/usr/bin/env python3
"""Render a local preview of the real plugin templates.

Reads the actual src/*.liquid files and data/days.json, so the preview always
reflects what is deployed — it cannot drift from the templates the way a
hand-copied preview would.

Usage:
    python3 scripts/preview.py                    # today, full layout
    python3 scripts/preview.py 10-31              # a specific day
    python3 scripts/preview.py 10-31 quadrant     # a specific layout
    python3 scripts/preview.py --all              # every layout, today
    python3 scripts/preview.py --devices          # FULL on OG, TRMNL X, X portrait

Writes preview/preview.html — open it in a browser.

Note: this implements only the small subset of Liquid these templates use
(assign, if/else, dotted and bracket lookups, and the date/plus/upcase/
truncate filters). It is a preview aid, not a general Liquid engine; TRMNL
itself renders with real Liquid.
"""
import json
import re
import sys
import time
import calendar
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS_URL = "https://trmnl.com/css/latest/plugins.css"
CSS_MAX_AGE = 7 * 24 * 3600  # re-download the cached framework CSS weekly

# Device/orientation matrix. TRMNL gates responsive classes on screen classes:
# `lg:` needs .screen--lg, portrait variants need .screen--portrait, and the
# cqw/cqh units resolve against .layout (container-type: size).
DEVICES = {
    "og":         {"label": "OG 800x480",            "w": 800,  "h": 480,  "cls": "screen--og screen--sm screen--1bit"},
    "x_landscape":{"label": "TRMNL X 1040x780",      "w": 1040, "h": 780,  "cls": "screen--v2 screen--lg"},
    "x_portrait": {"label": "TRMNL X portrait 780x1040", "w": 780, "h": 1040, "cls": "screen--v2 screen--lg screen--portrait"},
}

# TRMNL screen sizes, in pixels
SIZES = {
    "full": (800, 480),
    "half_horizontal": (800, 240),
    "half_vertical": (400, 480),
    "quadrant": (400, 240),
}

# Seconds to add to UTC when previewing (TRMNL supplies trmnl.user.utc_offset).
UTC_OFFSET = -7 * 3600


# --------------------------------------------------------------------------
# A deliberately small Liquid subset
# --------------------------------------------------------------------------

def resolve(expr, ctx):
    """Resolve a literal or a variable path like days[mmdd] or entry.title."""
    expr = expr.strip()
    if not expr:
        return ""
    if (expr[0] == expr[-1] == '"') or (expr[0] == expr[-1] == "'"):
        return expr[1:-1]
    if re.fullmatch(r"-?\d+", expr):
        return int(expr)

    # split on dots and [...] segments
    parts = re.findall(r"[^.\[\]]+|\[[^\]]+\]", expr)
    val = ctx
    for p in parts:
        if p.startswith("["):
            key = resolve(p[1:-1], ctx)
        else:
            key = p
        if isinstance(val, dict):
            val = val.get(key if isinstance(key, str) else str(key))
        else:
            val = getattr(val, str(key), None)
        if val is None:
            return None
    return val


def apply_filter(val, name, arg, ctx):
    if name == "date":
        fmt = resolve(arg, ctx)
        if val == "now":
            val = int(time.time())
        return time.strftime(fmt, time.gmtime(int(val)))
    if name == "plus":
        return int(val) + int(resolve(arg, ctx) or 0)
    if name == "minus":
        return int(val) - int(resolve(arg, ctx) or 0)
    if name == "upcase":
        return str(val).upper()
    if name == "downcase":
        return str(val).lower()
    if name == "truncate":
        n = int(resolve(arg, ctx))
        s = str(val)
        return s if len(s) <= n else s[: max(n - 3, 0)] + "..."
    raise ValueError(f"preview.py does not implement the '{name}' filter")


def evaluate(expr, ctx):
    """Evaluate 'value | filter: arg | filter2'."""
    # split on | that are not inside quotes
    parts = re.split(r"\|(?=(?:[^\"']*[\"'][^\"']*[\"'])*[^\"']*$)", expr)
    val = resolve(parts[0], ctx)
    for f in parts[1:]:
        f = f.strip()
        if ":" in f:
            name, arg = f.split(":", 1)
        else:
            name, arg = f, ""
        val = apply_filter(val, name.strip(), arg.strip(), ctx)
    return val


def render(tpl, ctx):
    """Render assigns, if/else blocks, and {{ }} output."""
    # {% assign x = ... %}
    def do_assign(m):
        ctx[m.group(1)] = evaluate(m.group(2), ctx)
        return ""

    # Process assigns and conditionals in document order.
    out, pos = [], 0
    tag = re.compile(r"\{%-?\s*(assign|if|else|endif)\b(.*?)-?%\}", re.S)
    while True:
        m = tag.search(tpl, pos)
        if not m:
            out.append(tpl[pos:])
            break
        out.append(tpl[pos : m.start()])
        kind, body = m.group(1), m.group(2).strip()

        if kind == "assign":
            name, expr = body.split("=", 1)
            ctx[name.strip()] = evaluate(expr, ctx)
            pos = m.end()

        elif kind == "if":
            # find matching else/endif at the same nesting depth
            depth, i = 1, m.end()
            else_at = None
            while depth:
                m2 = tag.search(tpl, i)
                if not m2:
                    raise ValueError("unclosed {% if %}")
                k = m2.group(1)
                if k == "if":
                    depth += 1
                elif k == "else" and depth == 1:
                    else_at = (m2.start(), m2.end())
                elif k == "endif":
                    depth -= 1
                    if depth == 0:
                        end_at = (m2.start(), m2.end())
                i = m2.end()

            if else_at:
                truthy = tpl[m.end() : else_at[0]]
                falsy = tpl[else_at[1] : end_at[0]]
            else:
                truthy, falsy = tpl[m.end() : end_at[0]], ""

            val = evaluate(body, ctx)
            chosen = truthy if val not in (None, False, "") else falsy
            out.append(render(chosen, ctx))
            pos = end_at[1]

        else:  # stray else/endif (already consumed by the if branch)
            pos = m.end()

    text = "".join(out)
    return re.sub(r"\{\{-?\s*(.*?)\s*-?\}\}",
                  lambda m: str(evaluate(m.group(1), ctx) or ""), text)


# --------------------------------------------------------------------------

def framework_css(out_dir):
    """Cache plugins.css next to the preview.

    Browsers refuse to apply a remote stylesheet to a file:// page in some
    sandboxes, which silently produces an unstyled — and therefore misleading
    — preview. Referencing a local copy avoids that.
    """
    css = out_dir / "plugins.css"
    fresh = css.exists() and (time.time() - css.stat().st_mtime) < CSS_MAX_AGE
    if not fresh:
        try:
            req = urllib.request.Request(CSS_URL, headers={"User-Agent": "ThisDayInHorror/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                css.write_bytes(resp.read())
            print(f"  cached framework CSS ({css.stat().st_size // 1024} KB)")
        except Exception as e:
            if not css.exists():
                print(f"  WARNING: could not fetch framework CSS ({e});")
                print("           preview will be unstyled and NOT representative.")
                return CSS_URL
            print(f"  note: using cached framework CSS (refresh failed: {e})")
    return css.name


def build_context(mmdd, days):
    fixed = calendar.timegm(time.strptime(f"2024-{mmdd}", "%Y-%m-%d")) - UTC_OFFSET
    return {
        "days": days,
        "trmnl": {"user": {"utc_offset": UTC_OFFSET}},
        # make "now" resolve to the requested day so any date can be previewed
        "now": fixed,
        "__now__": fixed,
    }


def render_layout(layout, mmdd, days):
    tpl = (ROOT / "src" / f"{layout}.liquid").read_text()
    ctx = build_context(mmdd, days)
    # the templates start from the literal "now"; point it at the chosen day
    tpl = tpl.replace('"now" | date: "%s"', '__now__ | date: "%s"', 1)
    return render(tpl, ctx)


def main():
    args = [a for a in sys.argv[1:]]
    show_all = "--all" in args
    show_devices = "--devices" in args
    args = [a for a in args if a not in ("--all", "--devices")]
    devices = list(DEVICES) if show_devices else None
    mmdd = args[0] if args else time.strftime("%m-%d")
    layouts = list(SIZES) if show_all else [args[1] if len(args) > 1 else "full"]

    data = json.loads((ROOT / "data" / "days.json").read_text())
    days = data["days"]
    if mmdd not in days:
        sys.exit(f"no entry for {mmdd}")

    out_dir = ROOT / "preview"
    out_dir.mkdir(exist_ok=True)
    css_href = framework_css(out_dir)

    blocks = []
    if devices:
        for dev in devices:
            d = DEVICES[dev]
            for layout in layouts:
                # Slot geometry within the device screen
                w, h = d["w"], d["h"]
                if layout == "half_horizontal": h = h // 2
                elif layout == "half_vertical": w = w // 2
                elif layout == "quadrant":      w, h = w // 2, h // 2
                blocks.append(f"""
  <figure data-device="{dev}" data-layout="{layout}">
    <figcaption>{d['label']} &middot; {layout}</figcaption>
    <div class="screen {d['cls']}" style="width:{w}px;height:{h}px">
      <div class="view view--{layout}">{render_layout(layout, mmdd, days)}</div>
    </div>
  </figure>""")
    else:
        for layout in layouts:
            if layout not in SIZES:
                sys.exit(f"unknown layout {layout!r}; choose from {', '.join(SIZES)}")
            w, h = SIZES[layout]
            blocks.append(f"""
  <figure data-device="og" data-layout="{layout}">
    <figcaption>{layout} &middot; {w}&times;{h}</figcaption>
    <div class="screen screen--og screen--sm screen--1bit" style="width:{w}px;height:{h}px">
      <div class="view view--{layout}">{render_layout(layout, mmdd, days)}</div>
    </div>
  </figure>""")

    html = f"""<!doctype html>
<html><head>
<meta charset="utf-8">
<title>This Day in Horror — {mmdd}</title>
<link rel="stylesheet" href="{css_href}">
<style>
  body {{ background:#e5e5e5; margin:0; }}
  .gallery {{ font-family:system-ui,sans-serif; padding:32px;
              display:flex; flex-wrap:wrap; gap:32px; align-items:flex-start; }}
  .gallery figure {{ margin:0; }}
  .gallery figcaption {{ font-size:12px; color:#444; margin-bottom:6px;
                         font-family:ui-monospace,monospace; }}
  .gallery .screen {{ background:#fff; outline:10px solid #222; overflow:hidden; }}
</style>
</head><body>
<!-- The framework scopes every rule under .trmnl, so the wrapper is required. -->
<div class="trmnl gallery">{''.join(blocks)}
</div>
</body></html>"""

    out = out_dir / "preview.html"
    out.write_text(html)
    entry = days[mmdd]
    print(f"wrote {out}")
    print(f"  {mmdd}: {entry['title']} ({entry['year']}) — {', '.join(layouts)}")


if __name__ == "__main__":
    main()
