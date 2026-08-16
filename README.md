# This Day in Horror — TRMNL plugin

A TRMNL private plugin that shows one notable horror fact for every day of the
year — film releases, deaths/births of horror icons, publications, and dark
trivia — with a matching poster or portrait, auto-dithered for the e-ink screen.

There is no live "today in horror history" API, so this repo takes the
pre-built approach: a **366-day JSON dataset**, from which a small rolling
file is published hourly for the plugin to poll. The Liquid template picks the
right entry using the device owner's timezone — see
["Why current.json exists"](#why-currentjson-exists) for why the polled file
has to keep changing.

## How the dataset is built

- [data/curated.json](data/curated.json) — ~70 hand-written entries for iconic
  dates (Halloween premiering Oct 25 1978, Poe's death, the War of the Worlds
  broadcast, the Salem witch warrants on leap day...). These always win.
- [scripts/build.py](scripts/build.py) — fills every remaining day by querying
  **Wikidata** for the most notable horror film (by Wikipedia sitelink count)
  with an exact release date on that day, then fetches each entry's lead image
  (poster/portrait) from **Wikipedia** and bakes the URL in.
- [data/current.json](data/current.json) — **this is the file the plugin polls.**
  A GitHub Actions workflow ([refresh.yml](.github/workflows/refresh.yml)) runs
  [scripts/make_current.py](scripts/make_current.py) hourly to regenerate it.
  See "Why current.json exists" below.
- Output: [data/days.json](data/days.json) — 366 entries, all with images, minified
  to ~86 KB. **TRMNL rejects polling responses over 100 KB**, so the build strips
  build-only fields and image query params; it prints a warning if the file grows
  past the limit. [data/days.full.json](data/days.full.json) keeps the unminified
  copy (with `wiki`/`source` fields) for maintenance — the plugin does not use it.

Rebuild any time with:

```bash
python3 scripts/build.py
```

## Why current.json exists

TRMNL **skips re-rendering a screen when the polled response is unchanged** —
the device logs show `Skipping: No change in data`. A completely static dataset
is therefore rendered once and then frozen on that day forever, even though the
template computes the date itself. That is not a caching quirk to wait out; the
payload has to change for the screen to be redrawn at all.

So the plugin polls a small rolling file instead:

- `data/current.json` (~750 bytes) holds a timestamp plus a **three-day window**
  of entries — yesterday, today and tomorrow in UTC.
- A workflow regenerates it **every 15 minutes** with a minute-precision
  timestamp, so every run produces a distinct payload.
- The templates are unchanged: they still look up `days["MM-DD"]` using the
  *viewer's* local date via `trmnl.user.utc_offset`. A ±1 day window covers
  every timezone from UTC-12 to UTC+14, so the plugin stays correct worldwide.

### Cadence

Because the payload changes every 15 minutes and devices poll on their own
schedule (5–15 minutes), a device re-renders on essentially **every** check —
so it picks up the new local date within minutes of midnight, not hours.

Hourly was the obvious first choice and is **not** sufficient: local midnight
falls on a *half-hour* UTC boundary in some timezones (India, parts of
Australia), which would leave those viewers on yesterday's fact until roughly
00:50 local. GitHub also delays scheduled runs under load, which eats any
thinner margin. Fifteen minutes leaves room for both.

## Setup

### 1. Host the data publicly

Push this folder to GitHub, and **enable Actions** on the repo so the hourly
refresh workflow can run (it needs write access to commit `data/current.json`;
the workflow already requests `permissions: contents: write`).

This project lives at
[github.com/CoffinDeliveryService/this-day-in-horror](https://github.com/CoffinDeliveryService/this-day-in-horror),
and the polling URL is:

```
https://raw.githubusercontent.com/CoffinDeliveryService/this-day-in-horror/main/data/current.json
```

### 2. Create the private plugin on TRMNL

1. usetrmnl.com → **Plugins → Private Plugin → Add New**
2. Name: `This Day in Horror`
3. Strategy: **Polling**, Polling URL: the raw URL above
4. Max refresh rate: **every 15 mins** — the fact only changes at midnight, but
   the device must poll often enough to notice the hourly payload change soon
   after your local midnight
5. **Edit Markup** and paste each file from [src/](src/) into the matching
   layout tab: `full.liquid`, `half_horizontal.liquid`, `half_vertical.liquid`,
   `quadrant.liquid`
6. Save, then add the plugin to your playlist.

### 3. Preview locally (optional)

```bash
python3 scripts/preview.py 10-31 --all
```

Writes `preview/preview.html` — open it in a browser. Arguments are optional:
a `MM-DD` date (defaults to today) and a layout name (defaults to `full`);
`--all` renders all four layouts side by side at their true pixel sizes.

The preview renders the **actual `src/*.liquid` templates** against the real
dataset, so it cannot drift from what is deployed. It caches the TRMNL
framework CSS into `preview/` on first run (~17 MB, git-ignored) and wraps the
screens in `.trmnl`, which the framework requires — without that wrapper none
of its rules apply and the preview silently renders unstyled.

It implements only the small slice of Liquid these templates use (`assign`,
`if`/`else`, dotted and bracket lookups, and the `date`, `plus`, `upcase`, and
`truncate` filters) — enough to preview, but TRMNL itself renders with real
Liquid, so treat the on-device result as the source of truth.

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
