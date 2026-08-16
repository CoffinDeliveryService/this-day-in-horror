#!/usr/bin/env python3
"""Generate data/current.json — the small file the TRMNL plugin actually polls.

Why this exists
---------------
TRMNL skips re-rendering a screen when a polled response is byte-identical to
the previous one ("Skipping: No change in data" in the device logs). A static
366-day dataset therefore renders once and then freezes on that day forever,
even though the template computes the date itself.

So the polled payload has to change over time. This script emits a tiny file
containing a timestamp plus a three-day window of entries (yesterday, today and
tomorrow in UTC). A workflow regenerates it hourly, which:

  * changes the payload every hour, so TRMNL re-renders and the template
    re-evaluates the date;
  * still lets the template look up days[MM-DD] using the *viewer's* local
    date, so the plugin stays correct in every timezone (UTC-12..UTC+14 are
    all covered by a +/- 1 day window);
  * keeps the response well under TRMNL's 100 KB polling limit, and keeps the
    hourly commits tiny.

Run:  python3 scripts/make_current.py
"""
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    days = json.loads((ROOT / "data" / "days.json").read_text())["days"]

    now = datetime.now(timezone.utc)
    window = {}
    for delta in (-1, 0, 1):
        key = (now + timedelta(days=delta)).strftime("%m-%d")
        if key in days:
            window[key] = days[key]

    # Feb 29 only exists in leap years; make sure a non-leap Mar 1 still has a
    # neighbouring entry to fall back on.
    if "02-29" in days and now.strftime("%m-%d") in ("02-28", "03-01"):
        window.setdefault("02-29", days["02-29"])

    out = {
        # Minute precision: every workflow run emits a distinct value, so the
        # payload always differs and TRMNL always re-renders. Running this every
        # 15 minutes means a device polling every 15 minutes re-renders on
        # essentially every check, so the date is picked up within minutes of
        # the viewer's local midnight — including half-hour timezones.
        "generated": now.strftime("%Y-%m-%dT%H:%M:00Z"),
        "days": window,
    }

    path = ROOT / "data" / "current.json"
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"wrote {path} ({path.stat().st_size} bytes)")
    print(f"  generated: {out['generated']}")
    print(f"  window:    {', '.join(sorted(window))}")


if __name__ == "__main__":
    main()
