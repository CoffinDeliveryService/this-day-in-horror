#!/usr/bin/env python3
"""Add an `orientation` flag to every entry.

The dataset mixes tall film posters with landscape stills and square-ish
portraits. A single set of sizing classes cannot flatter all three, so the
templates branch on this flag (Liquid if/else) and size each shape to fill the
space properly. Run after build.py.
"""
import json, time, urllib.request, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEADERS = {"User-Agent": "ThisDayInHorror/1.0 (personal TRMNL e-ink plugin)"}


def http_json(url):
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 4:
                wait = 20 * (attempt + 1)
                print(f"  rate limited, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


def fetch_dims(titles):
    """Return {article_title: (width, height)} for the lead image thumbnail."""
    dims, titles = {}, list(dict.fromkeys(titles))
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "titles": "|".join(batch),
            "prop": "pageimages", "piprop": "thumbnail",
            "pithumbsize": 480, "pilimit": "max", "pilicense": "any",
            "redirects": 1, "format": "json",
        })
        data = http_json(url)
        q = data["query"]
        back = {}
        for n in q.get("normalized", []) + q.get("redirects", []):
            back[n["to"]] = back.get(n["from"], n["from"])
        for page in q["pages"].values():
            name = page.get("title", "")
            thumb = page.get("thumbnail")
            if not thumb:
                continue
            wh = (thumb["width"], thumb["height"])
            dims[name] = wh
            dims[back.get(name, name)] = wh
        time.sleep(0.5)
    return dims


def classify(w, h):
    ratio = w / h
    if ratio <= 0.85:
        return "portrait"     # film posters — the majority
    if ratio >= 1.18:
        return "landscape"    # stills, wide photos
    return "square"


def main():
    full_path = ROOT / "data" / "days.full.json"
    full = json.loads(full_path.read_text())
    days = full["days"]

    print(f"fetching image dimensions for {len(days)} entries...")
    dims = fetch_dims([e["wiki"] for e in days.values()])

    counts, missing = {}, []
    for key, e in sorted(days.items()):
        wh = dims.get(e["wiki"])
        if not wh:
            e["orientation"] = "portrait"   # safe default: most art is a poster
            missing.append(f"{key} ({e['wiki']})")
        else:
            e["orientation"] = classify(*wh)
            e["aspect"] = round(wh[0] / wh[1], 3)
        counts[e["orientation"]] = counts.get(e["orientation"], 0) + 1

    full_path.write_text(json.dumps(full, ensure_ascii=False, indent=1))
    print("orientation counts:", counts)
    if missing:
        print(f"no dimensions for {len(missing)} (defaulted to portrait):")
        for m in missing[:10]:
            print("  ", m)

    # lean copies used by the plugin
    lean = {"generated": full.get("generated"), "days": {}}
    for k, e in sorted(days.items()):
        lean["days"][k] = {
            "year": e["year"], "category": e["category"], "title": e["title"],
            "fact": e["fact"], "image": e["image"].split("?")[0],
            "orientation": e["orientation"],
        }
    p = ROOT / "data" / "days.json"
    p.write_text(json.dumps(lean, ensure_ascii=False, separators=(",", ":")))
    print(f"wrote {p} ({p.stat().st_size // 1024} KB)")

    sp = ROOT / "data" / "static_data.json"
    sp.write_text(json.dumps({"days": lean["days"]}, ensure_ascii=False, separators=(",", ":")))
    size = sp.stat().st_size
    print(f"wrote {sp} ({size // 1024} KB)"
          + ("  WARNING: over 100KB!" if size > 100_000 else ""))


if __name__ == "__main__":
    main()
