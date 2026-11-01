"""Turn the resort's calendar feed(s) into booked.json for the website.

AIRBNB_ICAL holds one or more iCal export links (Airbnb, or any other calendar
that exports .ics), separated by spaces or new lines. Only the dates leave this
script: no guest names, no booking codes. Each range is [first night, check-out
day), matching how the site reads it. booked.json is rewritten only when the
dates change, so the repo is not committed to every hour for nothing.
"""
import datetime as dt, json, os, sys, urllib.request

urls = os.environ.get("AIRBNB_ICAL", "").split()
if not urls:
    print("No calendar link set yet (secret AIRBNB_ICAL). Nothing to do.")
    sys.exit(0)

def day(v):
    v = v.split(":")[-1].strip()[:8]
    return dt.date(int(v[:4]), int(v[4:6]), int(v[6:8]))

ranges = []
for url in urls:
    req = urllib.request.Request(url, headers={"User-Agent": "treerings-calendar-sync"})
    text = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    lines = []
    for raw in text.splitlines():               # undo iCal line folding
        if raw[:1] in (" ", "\t") and lines: lines[-1] += raw[1:]
        else: lines.append(raw)
    start = end = None
    for ln in lines:
        if ln.startswith("BEGIN:VEVENT"): start = end = None
        elif ln.startswith("DTSTART"): start = day(ln)
        elif ln.startswith("DTEND"): end = day(ln)
        elif ln.startswith("END:VEVENT") and start:
            ranges.append([start, end if end and end > start else start + dt.timedelta(days=1)])

today = dt.date.today()
ranges = sorted(r for r in ranges if r[1] > today)
merged = []
for s, e in ranges:
    if merged and s <= merged[-1][1]: merged[-1][1] = max(merged[-1][1], e)
    else: merged.append([s, e])
booked = [[s.isoformat(), e.isoformat()] for s, e in merged]

try:
    old = json.load(open("booked.json"))
except (OSError, ValueError):
    old = {}
if old.get("booked") == booked:
    print("No change in booked dates.")
    sys.exit(0)
json.dump({"updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "booked": booked},
          open("booked.json", "w"), indent=1)
print(f"Wrote {len(booked)} booked ranges.")
