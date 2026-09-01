# This Day in Horror

A TRMNL plugin that puts one piece of horror history on your screen every morning —
a film that opened on this date, or the day the genre lost someone. Whatever the
day holds, you get the poster, the year, and the name, dithered for e-ink.

366 days are already written. February 29th included.

## How it works

There's no "today in horror history" API to call, so the whole calendar ships
inside the plugin as Static data. The Liquid template does the rest: on every
refresh it reads the clock, works out what day it is *where your device is*, and
pulls that entry.

That means there's nothing to host and nothing to keep running. No server, no
cron job, no dependency on this repo staying online. Set it up once and it keeps
working.

### Why Static and not Polling

This one bit me, so it's worth writing down.

TRMNL skips regenerating a screen when a polled response comes back unchanged —
you'll see `Skipping: No change in data` in the device logs. That's a sensible
optimisation, and it completely breaks a date-driven plugin: the data never
changes, so the screen renders once and then sits on that day forever, even
though the template is perfectly capable of working out the date.

Static data is [exempt from that skip](https://help.trmnl.com/en/articles/10113695-how-refresh-rates-work),
so every scheduled refresh really does re-render. Confirmed on-device: two
consecutive scheduled refreshes both regenerated with no data change and no
forced refresh.

## Setup

Nothing to host. Five minutes, start to finish.

1. On usetrmnl.com go to **Plugins → Private Plugin → Add New** and call it
   `This Day in Horror`.
2. Set **Strategy** to **Static** and paste
   [`data/static_data.json`](data/static_data.json) into the *Static data* field.
   Leave the polling URL empty.
3. Set the refresh rate to whatever you like. The screen re-renders every time,
   so the day rolls over within one refresh interval of your local midnight.
4. Open **Edit Markup** and paste each file from [`src/`](src/) into its matching
   tab: `full.liquid`, `half_horizontal.liquid`, `half_vertical.liquid`,
   `quadrant.liquid`.
5. Save and add it to your playlist.

## Where the entries come from

Two sources, and the hand-written ones take priority when both have something for
the same date.

[`data/curated.json`](data/curated.json) holds about 70 entries written by hand —
the dates worth getting right. Halloween opening in Kansas City in 1978. Poe
dying in Baltimore in clothes that weren't his. The Salem arrest warrants on leap
day. Houdini on Halloween.

[`scripts/build.py`](scripts/build.py) fills the rest. It asks Wikidata for horror
films with an exact release date on each remaining day, ranks them by how many
Wikipedia language editions they appear in, takes the most notable one, and grabs
the poster from Wikipedia.

Then [`scripts/add_orientation.py`](scripts/add_orientation.py) tags every entry
`portrait`, `landscape` or `square` from the real image dimensions — currently
348 / 14 / 4. The templates branch on that, which matters more than it sounds
like it should (see below).

```bash
python3 scripts/build.py
python3 scripts/add_orientation.py
```

That writes three files:

| File | What it's for |
| --- | --- |
| `data/static_data.json` | The one you paste into TRMNL |
| `data/days.json` | Same data, used by the local preview |
| `data/days.full.json` | Unminified, keeps `wiki`/`source`/`fact` for editing |

Keep the pasted file under **100 KB** — TRMNL rejects payloads bigger than that.
It currently sits around 67 KB.

## Designing for both screens

Every view works on TRMNL OG (800×480), TRMNL X (1040×780), and TRMNL X turned
portrait (780×1040) — the three configurations recipe reviewers check.

A few things I learned the hard way:

**Size images from the shape of the image.** Posters are tall, stills are wide,
and no single rule flatters both. Tall art is driven from height with the width
capped; wide art is driven from width with the height capped, and gets stacked
above the text so it can use the full column. `image--contain` letterboxes
whatever's left, so any aspect ratio is safe.

**Use container units, not pixels.** `w--[60cqw]` scales with the slot;
`w--40` is 160px forever. Mixing them is how you end up with a poster that
looks right on one device and postage-stamp-sized on another.

**Add `flex-none` to the image.** Without it the text column squeezes the image
and your carefully chosen `50cqw` quietly renders at 20%.

**`lg:` only fires on TRMNL X.** It's gated on a `.screen--lg` class, so BYOD
devices reporting `screen--md` fall through to your base classes. If the base is
a fixed pixel value, those devices never scale.

**Let the artwork carry it.** The auto-generated entries used to end with a
sentence like *"The Card Player first hit screens on this day in 2004"* directly
under a header reading *RELEASE • 2004* and a title reading *The Card Player*.
It said nothing, so it's gone, and the poster and title got bigger.

## Previewing locally

```bash
python3 scripts/preview.py                 # today, full view
python3 scripts/preview.py 10-31 --all     # every view, Halloween
python3 scripts/preview.py 12-03 --devices # every device and orientation
```

Open `preview/preview.html` in a browser.

It renders the real `src/*.liquid` files against the real data, so it can't drift
from what you've deployed. On first run it caches TRMNL's framework CSS and JS
into `preview/` (~17 MB, git-ignored) and wraps everything in `.trmnl` — the
framework scopes every rule under that class, and without it you get a page that
looks fine and is styled by nothing at all.

Two caveats worth knowing:

It implements only the slice of Liquid these templates use — `assign`,
`if`/`else` with `==`, dotted and bracket lookups, and the `date`, `plus`,
`upcase` and `truncate` filters. It's a preview, not a Liquid engine.

And it models screen size and text scale but *not* a device's `scale_factor` or
`ui_scale`. On BYOD hardware it under-predicts how large text renders, so for
those, check the actual PNG your device downloads from the dashboard before
trusting it.

## Changing an entry

Edit [`data/curated.json`](data/curated.json) — the key is `MM-DD`, and `wiki` is
the English Wikipedia article title the image is pulled from. Run the two scripts
above, then paste the new `static_data.json` back into the plugin.

To drop a film the automatic pass picked, add its Wikipedia title to `BLOCKLIST`
in `scripts/build.py` and rebuild. The next most notable film for that day takes
its place.

Categories in use: `release`, `death`, `birth`, `publication`, `trivia`.

## Notes

Automatic entries use each film's earliest exact release date on Wikidata, which
is occasionally a festival premiere rather than the wide release everyone
remembers. If a day bothers you, write over it in `curated.json`.

Posters are hot-linked from Wikipedia and Wikimedia. They're low-resolution
fair-use images, which is fine for a personal e-ink display.

Dates follow the timezone on your TRMNL account, via `trmnl.user.utc_offset`.
