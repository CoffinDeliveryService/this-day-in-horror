# This Day in Horror

A TRMNL plugin that shows one piece of horror history for the current date — a
film released that day, or a death or birth in the genre — with the poster art,
the year, and the title, dithered for e-ink.

Covers all 366 days. Works on TRMNL OG and TRMNL X, in both orientations, in all
four layouts.

## Setup

Nothing to host, no account to connect.

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
interval of your local midnight.

**Use Static, not Polling.** TRMNL skips regenerating a screen when a polled
response is unchanged (`Skipping: No change in data` in the device logs). Since
the dataset never changes, a polled version of this plugin would freeze on
whichever day it first rendered. Static data is
[exempt from that skip](https://help.trmnl.com/en/articles/10113695-how-refresh-rates-work)
and re-renders on every refresh.

The date comes from your TRMNL account timezone via `trmnl.user.utc_offset`, so
the template picks the right day wherever the device is.

## Building the dataset

Two sources. Hand-written entries take priority when both cover the same date.

- [`data/curated.json`](data/curated.json) — about 70 entries written by hand for
  the dates worth getting right: *Halloween* opening in Kansas City in 1978, Poe's
  death in Baltimore, the Salem arrest warrants on leap day, Houdini on Halloween.
- [`scripts/build.py`](scripts/build.py) — fills every remaining day. Queries
  Wikidata for horror films with an exact release date, ranks them by how many
  Wikipedia language editions they appear in, takes the most notable, and pulls
  the poster from Wikipedia.
- [`scripts/add_orientation.py`](scripts/add_orientation.py) — tags each entry
  `portrait`, `landscape` or `square` from the real image dimensions (currently
  348 / 14 / 4). The templates size images differently per tag.

```bash
python3 scripts/build.py
python3 scripts/add_orientation.py
```

Output:

| File | Purpose |
| --- | --- |
| `data/static_data.json` | Paste this into TRMNL |
| `data/days.json` | Same data, read by the local preview |
| `data/days.full.json` | Unminified, keeps `wiki`/`source`/`fact` for editing |

TRMNL rejects payloads over **100 KB**. `static_data.json` is currently ~67 KB;
`build.py` warns if a rebuild pushes it over.

## Editing entries

Edit [`data/curated.json`](data/curated.json). The key is `MM-DD`; `wiki` is the
English Wikipedia article title the image is pulled from. Categories in use:
`release`, `death`, `birth`, `publication`, `trivia`.

To replace a film the automatic pass chose, add its Wikipedia title to
`BLOCKLIST` in `scripts/build.py`. The next most notable film for that day takes
its place.

After either change, rerun both scripts and paste the new `static_data.json` back
into the plugin.

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

Limitations: it implements only the Liquid these templates use (`assign`,
`if`/`else` with `==`, dotted and bracket lookups, and the `date`, `plus`,
`upcase`, `truncate` filters), and it models screen size and text scale but not a
device's `scale_factor` or `ui_scale`. On BYOD hardware it under-predicts
rendered text size — check the PNG your device downloads from the dashboard
instead.

## Template notes

If you modify the layouts:

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
is sometimes a festival premiere rather than the wide release. Override any day
in `curated.json`.

Poster images are hot-linked from Wikipedia and Wikimedia at low resolution.
