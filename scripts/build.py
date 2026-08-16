#!/usr/bin/env python3
"""Build data/days.json for the This Day In Horror TRMNL plugin.

1. Loads hand-curated entries from data/curated.json (these always win).
2. Queries Wikidata for notable horror films with exact release dates and
   fills every remaining day of the year with the most notable film that
   premiered on that day (notability = Wikipedia sitelink count).
3. Fetches each entry's lead image (poster/portrait) from Wikipedia and
   bakes the URL into the JSON.

Run:  python3 scripts/build.py
"""
import json
import time
import calendar
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEADERS = {"User-Agent": "ThisDayInHorror/1.0 (personal TRMNL e-ink plugin)"}
MIN_SITELINKS = 1  # floor for auto-filled films (top pick per day is by sitelinks anyway)

# Films Wikidata tags as "horror" that don't belong on a horror calendar
BLOCKLIST = {
    "Apocalypse Now", "Gravity (2013 film)", "Memento (film)",
    "Mulholland Drive (film)", "Blood Simple", "Blue Velvet (film)",
    "The Name of the Rose (film)", "The Girl on the Train (2016 film)",
    "Scoob!", "Cape Fear (1962 film)", "The Bone Collector",
    "One Hour Photo", "The Ghost and the Darkness", "The Naked Jungle",
    "Kalifornia", "The Deep (1977 film)", "Backrooms (film)",
    "Hotel Transylvania: Transformania", "The Snowman (2017 film)",
    "The Lovely Bones (film)",
}

SPARQL = """
SELECT ?film ?date ?sitelinks ?title WHERE {
  ?film wdt:P136 wd:Q200092 .
  ?film p:P577/psv:P577 ?dateNode .
  ?dateNode wikibase:timePrecision 11 ;
            wikibase:timeValue ?date .
  ?film wikibase:sitelinks ?sitelinks .
  FILTER(?sitelinks >= %d)
  ?article schema:about ?film ;
           schema:isPartOf <https://en.wikipedia.org/> ;
           schema:name ?title .
}
""" % MIN_SITELINKS


def http_json(url):
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 4:
                wait = 20 * (attempt + 1)
                print(f"  rate limited, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


def fetch_films():
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode(
        {"query": SPARQL, "format": "json"}
    )
    rows = http_json(url)["results"]["bindings"]
    films = {}  # qid -> {date, sitelinks, title}
    for r in rows:
        qid = r["film"]["value"].rsplit("/", 1)[-1]
        date = r["date"]["value"][:10]  # YYYY-MM-DD
        year = int(date[:4])
        if year < 1895 or date > time.strftime("%Y-%m-%d"):
            continue
        cur = films.get(qid)
        # keep the earliest full-precision date per film (= premiere)
        if cur is None or date < cur["date"]:
            films[qid] = {
                "date": date,
                "sitelinks": int(r["sitelinks"]["value"]),
                "title": r["title"]["value"],
            }
        elif date == cur["date"]:
            cur["sitelinks"] = max(cur["sitelinks"], int(r["sitelinks"]["value"]))
    return films


def clean_title(wiki_title):
    # "Halloween (1978 film)" -> "Halloween"
    if wiki_title.endswith(")") and "(" in wiki_title:
        base = wiki_title[: wiki_title.rfind("(")].strip()
        if base:
            return base
    return wiki_title


def all_days():
    for m in range(1, 13):
        for d in range(1, calendar.monthrange(2024, m)[1] + 1):  # 2024 = leap year
            yield f"{m:02d}-{d:02d}"


def fetch_images(titles):
    """Wikipedia lead images (posters/portraits) for a list of article titles."""
    images = {}
    titles = list(dict.fromkeys(titles))
    for i in range(0, len(titles), 50):
        batch = titles[i : i + 50]
        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
            {
                "action": "query",
                "titles": "|".join(batch),
                "prop": "pageimages",
                "piprop": "thumbnail",
                "pithumbsize": 480,
                "pilimit": "max",
                "pilicense": "any",
                "redirects": 1,
                "format": "json",
            }
        )
        data = http_json(url)
        # map redirected/normalized names back to what we asked for
        back = {}
        for n in data["query"].get("normalized", []) + data["query"].get("redirects", []):
            back[n["to"]] = back.get(n["from"], n["from"])
        for page in data["query"]["pages"].values():
            name = page.get("title", "")
            orig = back.get(name, name)
            thumb = page.get("thumbnail", {}).get("source")
            if thumb:
                images[orig] = thumb
                images[name] = thumb
        time.sleep(0.5)
    return images


def main():
    curated = json.loads((ROOT / "data" / "curated.json").read_text())
    print(f"curated entries: {len(curated)}")

    print("querying Wikidata for horror films (this can take a minute)...")
    films = fetch_films()
    print(f"films with exact dates: {len(films)}")

    # films already covered by a curated day must not fill a second day
    curated_wikis = {e["wiki"] for e in curated.values()}
    curated_titles = {e["title"].lower() for e in curated.values()}

    # bucket auto candidates by MM-DD
    by_day = {}
    for f in films.values():
        if f["title"] in BLOCKLIST:
            continue
        if f["title"] in curated_wikis or clean_title(f["title"]).lower() in curated_titles:
            continue
        key = f["date"][5:]
        by_day.setdefault(key, []).append(f)
    for cands in by_day.values():
        cands.sort(key=lambda f: -f["sitelinks"])

    days, missing = {}, []
    for key in all_days():
        if key in curated:
            e = dict(curated[key])
            e["source"] = "curated"
            days[key] = e
        elif by_day.get(key):
            top = by_day[key][0]
            title = clean_title(top["title"])
            year = int(top["date"][:4])
            days[key] = {
                "year": year,
                "category": "release",
                "title": title,
                "fact": f"{title} first hit screens on this day in {year}.",
                "wiki": top["title"],
                "source": "wikidata",
            }
        else:
            missing.append(key)

    print(f"filled: {len(days)}/366  (curated {len(curated)}, missing {len(missing)})")
    if missing:
        print("days with no entry:", ", ".join(missing))

    print("fetching Wikipedia images...")
    images = fetch_images([e["wiki"] for e in days.values()])
    no_image = []
    for key, e in days.items():
        e["image"] = images.get(e["wiki"], "")
        if not e["image"]:
            no_image.append(f"{key} ({e['wiki']})")
    if no_image:
        print(f"no image for {len(no_image)} entries:")
        for line in no_image:
            print("  ", line)

    out = {
        "generated": time.strftime("%Y-%m-%d"),
        "days": {k: days[k] for k in sorted(days)},
    }
    # rich copy for maintenance (keeps wiki/source fields)
    full_path = ROOT / "data" / "days.full.json"
    full_path.write_text(json.dumps(out, ensure_ascii=False, indent=1))

    # lean copy for TRMNL — polling responses must stay under 100 KB
    for e in out["days"].values():
        e["image"] = e["image"].split("?")[0]
        e.pop("wiki", None)
        e.pop("source", None)
    out_path = ROOT / "data" / "days.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    size = out_path.stat().st_size
    print(f"wrote {out_path} ({size // 1024} KB)" + ("  WARNING: exceeds TRMNL 100KB polling limit!" if size > 100_000 else ""))


if __name__ == "__main__":
    main()
