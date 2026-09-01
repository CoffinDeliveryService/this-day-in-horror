# This Day in Horror

A TRMNL plugin that shows one piece of horror history for the current date — a
film released that day, or a birth or death in the genre — with an image, the
year, and the title, dithered for e-ink.

## Install

Nothing to host, no account to connect, no maintenance. The full year ships
inside the plugin.

1. On usetrmnl.com go to **Plugins → Private Plugin → Add New** and name it
   `This Day in Horror`.
2. Set **Strategy** to **Static**. Leave the polling URL empty.
3. Paste the contents of [`data/static_data.json`](data/static_data.json) into
   the *Static data* field.
4. Open **Edit Markup** and paste each file from [`src/`](src/) into the matching
   tab: `full.liquid`, `half_horizontal.liquid`, `half_vertical.liquid`,
   `quadrant.liquid`.
5. Save, then add the plugin to a playlist.

Set the refresh rate to anything you like. The day rolls over within one refresh
interval of your local midnight. The date comes from your TRMNL account timezone
via `trmnl.user.utc_offset`.

**Strategy must be Static.** TRMNL skips regenerating a screen when a polled
response is unchanged (`Skipping: No change in data` in the device logs). Because
the dataset never changes, a polled version of this plugin would freeze on
whichever day it first rendered. Static data is
[exempt from that skip](https://help.trmnl.com/en/articles/10113695-how-refresh-rates-work)
and re-renders every time.

That's the whole install. Everything below is only for changing what a day shows.

---

## Changing a day

Add or replace an entry in [`data/curated.json`](data/curated.json), keyed by
`MM-DD`:

```json
"10-25": {
  "year": 1978,
  "category": "release",
  "title": "Halloween",
  "wiki": "Halloween (1978 film)",
  "fact": "John Carpenter's Halloween premiered in Kansas City in 1978, shot in just twenty days."
}
```

`title` and `year` are what appear on screen. `wiki` is the English Wikipedia
article title the image is pulled from. `category` is the small header label —
one of `release`, `death`, `birth`, `publication`, `trivia`. `fact` is kept for
reference and is not currently rendered on any layout.

To reject a film the generator picked without writing a replacement, add its
Wikipedia title to `BLOCKLIST` in [`scripts/build.py`](scripts/build.py). The
next most notable film for that date takes its place.

Then rebuild and paste the new `static_data.json` back into the plugin:

```bash
python3 scripts/build.py
python3 scripts/add_orientation.py
```

## How the 366 days are assembled

`build.py` produces one entry for every date, from two sources:

| Source | Days | How |
| --- | --- | --- |
| `data/curated.json` | 70 | Written by hand — the dates worth getting right |
| Wikidata | 296 | Every remaining date, filled automatically |

Curated entries win when both sources have something for the same date.

For the automatic 296, `build.py` queries Wikidata for horror films with an exact
release date, ranks the candidates for each date by how many Wikipedia language
editions they appear in, keeps the most notable one, and pulls its lead image
from Wikipedia. `add_orientation.py` then tags every entry `portrait`, `landscape` or
`square` from the real image dimensions (currently 348 / 14 / 4); the templates
size images differently per tag.

Output:

| File | Purpose |
| --- | --- |
| `data/static_data.json` | The file you paste into TRMNL |
| `data/days.json` | Same data, read by the local preview |
| `data/days.full.json` | Unminified, keeps `wiki`/`source`/`fact` for editing |

TRMNL rejects payloads over **100 KB**. `static_data.json` is currently ~67 KB;
`build.py` warns if a rebuild pushes it over.

## Local preview

```bash
python3 scripts/preview.py                 # today, full view
python3 scripts/preview.py 10-31 --all     # every view, Halloween
python3 scripts/preview.py 12-03 --devices # every device and orientation
```

Open `preview/preview.html` in a browser.

It renders the actual `src/*.liquid` files against the actual data, so it can't
drift from what's deployed. First run caches TRMNL's framework CSS and JS into
`preview/` (~17 MB, git-ignored) and wraps output in `.trmnl`, which the
framework requires — without that class every rule is unscoped and the page
renders unstyled.

Two limits: it implements only the Liquid these templates use (`assign`,
`if`/`else` with `==`, dotted and bracket lookups, and the `date`, `plus`,
`upcase`, `truncate` filters), and it models screen size and text scale but not a
device's `scale_factor` or `ui_scale`. On BYOD hardware it under-predicts
rendered text size — check the PNG your device downloads from the dashboard
instead.

## Editing the layouts

- **Images are sized by orientation.** Portrait art is driven from height with the
  width capped; landscape art is driven from width with the height capped and
  stacks above the text to use the full column. `image--contain` letterboxes the
  remainder, so any aspect ratio is safe.
- **Use container units, not fixed pixels.** `w--[60cqw]` scales with the slot;
  `w--40` is 160px on every device.
- **Keep `flex-none` on the image.** Without it the text column shrinks the image
  and the specified width silently doesn't apply.
- **`lg:` only applies on TRMNL X.** It's gated on a `.screen--lg` class. BYOD
  devices reporting `screen--md` fall through to the base classes, so the base
  classes must scale too.

## Caveats

Automatic entries use each film's earliest exact release date on Wikidata, which
is sometimes a festival premiere rather than the wide release. Override any date
in `curated.json`.

Images are hot-linked from Wikipedia and Wikimedia at low resolution. Most are
posters; some are stills or portraits, which is why entries carry an orientation
tag.
