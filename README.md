# This Day in Horror — TRMNL plugin

A TRMNL private plugin that shows one notable horror fact for every day of the
year — film releases, deaths/births of horror icons, publications, and dark
trivia — with a matching poster or portrait, auto-dithered for the e-ink screen.

There is no live "today in horror history" API, so this repo takes the
pre-built approach: a **366-day JSON dataset** that the plugin polls once a
day. The Liquid template picks today's entry itself using the device owner's
timezone, so the JSON never needs daily updates.

## How the dataset is built

- [data/curated.json](data/curated.json) — ~70 hand-written entries for iconic
  dates (Halloween premiering Oct 25 1978, Poe's death, the War of the Worlds
  broadcast, the Salem witch warrants on leap day...). These always win.
- [scripts/build.py](scripts/build.py) — fills every remaining day by querying
  **Wikidata** for the most notable horror film (by Wikipedia sitelink count)
  with an exact release date on that day, then fetches each entry's lead image
  (poster/portrait) from **Wikipedia** and bakes the URL in.
- Output: [data/days.json](data/days.json) — 366 entries, all with images, minified
  to ~86 KB. **TRMNL rejects polling responses over 100 KB**, so the build strips
  build-only fields and image query params; it prints a warning if the file grows
  past the limit. [data/days.full.json](data/days.full.json) keeps the unminified
  copy (with `wiki`/`source` fields) for maintenance — the plugin does not use it.

Rebuild any time with:

```bash
python3 scripts/build.py
```

## Setup

### 1. Host `data/days.json` somewhere public

Easiest free option — push this folder to GitHub:

```bash
git add -A && git commit -m "This Day in Horror"
```

This project lives at
[github.com/CoffinDeliveryService/this-day-in-horror](https://github.com/CoffinDeliveryService/this-day-in-horror),
and the polling URL is:

```
https://raw.githubusercontent.com/CoffinDeliveryService/this-day-in-horror/main/data/days.json
```

### 2. Create the private plugin on TRMNL

1. usetrmnl.com → **Plugins → Private Plugin → Add New**
2. Name: `This Day in Horror`
3. Strategy: **Polling**, Polling URL: the raw URL above
4. Refresh rate: daily (the fact only changes at midnight)
5. **Edit Markup** and paste each file from [src/](src/) into the matching
   layout tab: `full.liquid`, `half_horizontal.liquid`, `half_vertical.liquid`,
   `quadrant.liquid`
6. Save, then add the plugin to your playlist.

### 3. Preview locally (optional)

```bash
python3 scripts/preview.py 10-31
```

Writes `preview/preview.html` (approximate 800×480 render) for any date.

## Customizing

- **Change any day**: add/edit an entry in `data/curated.json` (key `MM-DD`,
  fields `year, category, title, fact, wiki`) and rerun the build. `wiki` is
  the English Wikipedia article title, used to fetch the image.
- **Kick out a film**: add its Wikipedia title to `BLOCKLIST` in
  `scripts/build.py` and rebuild — the next most notable film for that day
  takes its place.
- Categories used: `release`, `death`, `birth`, `publication`, `trivia`.

## Notes & caveats

- Auto-filled dates are each film's **earliest exact release date on
  Wikidata** — occasionally a festival premiere rather than the famous wide
  release, and rarely a date may reflect a regional release. Curate over any
  day you disagree with.
- Images are hot-linked from Wikipedia/Wikimedia. Film posters there are
  low-resolution fair-use images; fine for a personal e-ink display.
- The template uses `trmnl.user.utc_offset`, so "today" follows the timezone
  configured on your TRMNL account.
