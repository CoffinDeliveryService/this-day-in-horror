# This Day in Horror — TRMNL plugin

A TRMNL private plugin that shows one notable horror fact for every day of the
year — film releases, deaths/births of horror icons, publications, and dark
trivia — with a matching poster or portrait, auto-dithered for the e-ink screen.

There is no live "today in horror history" API, so this repo takes the
pre-built approach: a **366-day JSON dataset**, embedded in the plugin as
Static data. The Liquid template picks the right entry on every refresh using
the device owner's timezone — see
["How the plugin gets its data"](#how-the-plugin-gets-its-data) for why Static
rather than polling.

## How the dataset is built

- [data/curated.json](data/curated.json) — ~70 hand-written entries for iconic
  dates (Halloween premiering Oct 25 1978, Poe's death, the War of the Worlds
  broadcast, the Salem witch warrants on leap day...). These always win.
- [scripts/build.py](scripts/build.py) — fills every remaining day by querying
  **Wikidata** for the most notable horror film (by Wikipedia sitelink count)
  with an exact release date on that day, then fetches each entry's lead image
  (poster/portrait) from **Wikipedia** and bakes the URL in.
- [scripts/add_orientation.py](scripts/add_orientation.py) — tags every entry with
  an `orientation` of `portrait`, `landscape` or `square`, read from the real
  Wikipedia image dimensions (currently 348 / 14 / 4). The templates branch on
  this so posters and wide stills are each sized to fill the view properly.
  Run it after `build.py`.
- [data/static_data.json](data/static_data.json) — **this is what goes into the
  plugin.** It is `days.json` wrapped as `{"days": …}`, ready to paste into
  TRMNL's *Static data* field. See "How the plugin gets its data" below.
- Output: [data/days.json](data/days.json) — 366 entries, all with images, minified
  to ~93 KB. **TRMNL rejects polling responses over 100 KB**, so the build strips
  build-only fields and image query params; it prints a warning if the file grows
  past the limit. [data/days.full.json](data/days.full.json) keeps the unminified
  copy (with `wiki`/`source` fields) for maintenance — the plugin does not use it.

Rebuild any time with:

```bash
python3 scripts/build.py
```

## How the plugin gets its data

The plugin uses TRMNL's **Static** strategy: the whole 366-day dataset lives in
the plugin's *Static data* field, and there is no polling URL.

This is not just simpler — it is the only arrangement that is *reliably*
correct. TRMNL normally **skips re-rendering a screen when the polled response
is unchanged** (`Skipping: No change in data` in the device logs), so a static
dataset served over a polling URL renders once and then freezes on that day
forever, even though the template computes the date itself. Static data is
[explicitly exempt from that skip](https://help.trmnl.com/en/articles/10113695-how-refresh-rates-work),
so **every scheduled device refresh regenerates the screen**.

That gives the property that matters: whenever the device checks in — on
whatever interval its owner set — the template runs, reads that moment's date
through `trmnl.user.utc_offset`, and renders that viewer's local day. No
dependency on a payload changing, on a cron job firing, or on this repo staying
reachable.

Verified on-device: consecutive scheduled refreshes at 17:48:54 and 18:04:34 UTC
both regenerated the screen with no data change and no forced refresh.

### Maintenance: none

Nothing has to run for this plugin to keep working. There is no server, no
scheduled job, and no dependency on this repo staying online. The dataset
covers all 366 days and the facts are historical, so once the plugin is set up
it stays correct indefinitely — for you and for anyone who installs it.

The only reason to come back here is if you want to **change** a fact. That is
optional, not upkeep: edit [data/curated.json](data/curated.json), run
`python3 scripts/build.py`, and paste the regenerated
[data/static_data.json](data/static_data.json) into the plugin's *Static data*
field to publish it.

## Responsive: OG and TRMNL X

Every view is built to work on TRMNL OG (800x480), TRMNL X (1040x780), and
TRMNL X rotated to portrait (780x1040).

- **Images are bounded on both axes** using container-relative (`cqw`/`cqh`)
  values at `lg:`, so the artwork grows with the larger screen instead of
  staying pinned to a fixed pixel size, and `w--max-` / `h--max-` constraints
  stop it overshooting. `image--contain` letterboxes inside the box, so any
  aspect ratio is safe.

- **The image branches on `entry.orientation`** (Liquid `if`/`else`). Tall
  posters are driven from height (`h--96 lg:h--[85cqh]`, width capped) so they
  fill the view; wide stills are driven from width (`w--64 lg:w--[45cqw]`,
  height capped). One rule cannot flatter both shapes — a height-driven wide
  still blows out the row, and a width-driven poster overshoots vertically.
- **`flex-none` on the image** stops it being squeezed by long titles.
- **`lg:portrait:flex--col`** on the FULL row re-stacks image above text when
  TRMNL X is rotated.
- **Text scales with `lg:`** — label, value and description all step up on the
  larger screen (e.g. 16/58/12px on OG becomes 26/96/21px on X).
- **Facts are line-clamped, not character-truncated.** Each description carries
  `data-clamp` / `data-clamp-lg` / `data-clamp-lg-portrait`, so the framework
  trims by *rendered lines* against the actual slot. An earlier version used
  Liquid `truncate: N`, which cut mid-sentence with an ellipsis on most days
  regardless of how much room the display actually had.

  The clamp values are set so the longest entries still fit: across the 30
  worst-case days x 4 layouts x 3 devices (360 renders), **nothing overflows and
  nothing is ellipsed**. The clamp remains as a guarantee that no future edit can
  push text off-screen.

Verify locally across the whole matrix:

```bash
python3 scripts/preview.py 12-03 --all --devices
```

`--devices` renders every layout on OG, TRMNL X and TRMNL X portrait, applying
the same `screen--lg` / `screen--portrait` classes TRMNL uses to gate its
responsive rules.

## Setup

Nothing needs to be hosted — the data ships inside the plugin. This project
lives at
[github.com/CoffinDeliveryService/this-day-in-horror](https://github.com/CoffinDeliveryService/this-day-in-horror).

### 1. Create the private plugin on TRMNL

1. usetrmnl.com → **Plugins → Private Plugin → Add New**
2. Name: `This Day in Horror`
3. Strategy: **Static**, and paste the contents of
   [data/static_data.json](data/static_data.json) into the *Static data* field.
   Leave the polling URL empty.
4. Max refresh rate: whatever you like — the screen re-renders on every refresh,
   so the day rolls over within one refresh interval of your local midnight.
5. **Edit Markup** and paste each file from [src/](src/) into the matching
   layout tab: `full.liquid`, `half_horizontal.liquid`, `half_vertical.liquid`,
   `quadrant.liquid`
6. Save, then add the plugin to your playlist.

### 2. Preview locally (optional)

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
