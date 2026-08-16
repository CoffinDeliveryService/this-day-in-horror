#!/usr/bin/env python3
"""Render an approximate 800x480 preview of the full-layout screen.

Usage:  python3 scripts/preview.py [MM-DD]   (defaults to today)
Writes preview/preview.html — open it in a browser.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
key = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%m-%d")
entry = json.loads((ROOT / "data" / "days.json").read_text())["days"][key]
nice = time.strftime("%B %-d", time.strptime(f"2024-{key}", "%Y-%m-%d"))

html = f"""<!doctype html>
<html><head>
<meta charset="utf-8">
<title>TRMNL preview — {key}</title>
<link rel="stylesheet" href="https://usetrmnl.com/css/latest/plugins.css">
<style>
  body {{ background:#ddd; display:flex; justify-content:center; padding:40px; }}
  .screen {{ width:800px; height:480px; background:#fff; outline:12px solid #222;
             filter: grayscale(1) contrast(1.1); display:flex; flex-direction:column; }}
  .view {{ flex:1; display:flex; flex-direction:column; justify-content:center; }}
</style>
</head><body>
<div class="screen"><div class="view">
  <div class="layout layout--row" style="align-items:center; gap:24px; padding:0 10px; flex:1; display:flex;">
    <div style="flex:0 0 34%; display:flex; justify-content:center; align-items:center;">
      <img src="{entry['image']}" style="max-width:100%; max-height:370px; object-fit:contain;" />
    </div>
    <div style="flex:1; display:flex; flex-direction:column; gap:10px;">
      <span class="label label--underline">{entry['category'].upper()} &bull; {entry['year']}</span>
      <span class="value value--xlarge">{entry['title']}</span>
      <p class="description" style="font-size:20px; line-height:1.45;">{entry['fact']}</p>
    </div>
  </div>
  <div class="title_bar">
    <img class="image" src="https://usetrmnl.com/images/plugins/trmnl--render.svg" />
    <span class="title">This Day in Horror</span>
    <span class="instance">{nice}</span>
  </div>
</div></div>
</body></html>"""

out = ROOT / "preview" / "preview.html"
out.parent.mkdir(exist_ok=True)
out.write_text(html)
print(f"wrote {out} — {key}: {entry['title']} ({entry['year']})")
