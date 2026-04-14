"""
Live Bloomberg OIS/Offshore Data Feed
======================================

Polls Bloomberg every 10 minutes (or on bid/ask change via subscription).
Saves snapshots to data/live_ois.csv.

Usage:
    python scripts/live_feed.py              # poll mode (10 min intervals)
    python scripts/live_feed.py --subscribe  # real-time subscription mode
    python scripts/live_feed.py --once       # single snapshot and exit

Requirements:
    - Bloomberg Terminal running
    - pip install blpapi
"""

import argparse
import csv
import datetime as dt
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_FILE = DATA_DIR / "live_ois.csv"

# ── Ticker configuration ─────────────────────────────────────────────

OIS_TICKERS = {
    "1W":  {"sec": "TYSO1Z GFOF Curncy", "mo": 0,  "dy": 7},
    "2W":  {"sec": "TYSO2Z GFOF Curncy", "mo": 0,  "dy": 14},
    "1M":  {"sec": "TYSOA GFOF Curncy",  "mo": 1,  "dy": 0},
    "2M":  {"sec": "TYSOB GFOF Curncy",  "mo": 2,  "dy": 0},
    "3M":  {"sec": "TYSOC GFOF Curncy",  "mo": 3,  "dy": 0},
    "6M":  {"sec": "TYSOF GFOF Curncy",  "mo": 6,  "dy": 0},
    "9M":  {"sec": "TYSOI GFOF Curncy",  "mo": 9,  "dy": 0},
    "1Y":  {"sec": "TYSO1 GFOF Curncy",  "mo": 12, "dy": 0},
    "18M": {"sec": "TYSO1F GFOF Curncy", "mo": 18, "dy": 0},
    "2Y":  {"sec": "TYSO2 GFOF Curncy",  "mo": 24, "dy": 0},
    "3Y":  {"sec": "TYSO3 GFOF Curncy",  "mo": 36, "dy": 0},
    "4Y":  {"sec": "TYSO4 GFOF Curncy",  "mo": 48, "dy": 0},
    "5Y":  {"sec": "TYSO5 GFOF Curncy",  "mo": 60, "dy": 0},
}

OFFSHORE_TICKERS = {
    "ON":  {"sec": "TRYION Curncy",   "d": 0},
    "TN":  {"sec": "TRYITN Curncy",   "d": 1},
    "1W":  {"sec": "TRYI1W Curncy",   "d": 7},
    "2W":  {"sec": "TRYI2W Curncy",   "d": 14},
    "1M":  {"sec": "TRYI1M Curncy",   "d": 30},
    "2M":  {"sec": "TRYI2M Curncy",   "d": 63},
    "3M":  {"sec": "TRYI3M Curncy",   "d": 91},
    "6M":  {"sec": "TRYI6M Curncy",   "d": 183},
    "9M":  {"sec": "TRYI9M Curncy",   "d": 275},
    "1Y":  {"sec": "TRYI12M Curncy",  "d": 365},
    "18M": {"sec": "TRYI18M ICPL Curncy", "d": 548},
    "2Y":  {"sec": "TRYI2Y Curncy",   "d": 731},
    "3Y":  {"sec": "TRYI3Y Curncy",   "d": 1096},
}

TLREF_TICKER = "BISTTREF Index"
FIELDS = ["BID", "ASK", "MID"]


# ── Bloomberg helpers ─────────────────────────────────────────────────

def init_session():
    """Start Bloomberg session."""
    try:
        import blpapi
    except ImportError:
        print("ERROR: blpapi not installed. Run: pip install blpapi")
        sys.exit(1)

    opts = blpapi.SessionOptions()
    opts.setServerHost("localhost")
    opts.setServerPort(8194)
    session = blpapi.Session(opts)
    if not session.start():
        print("ERROR: Bloomberg session failed. Is Terminal running?")
        sys.exit(1)
    return session


def fetch_snapshot(session):
    """Fetch current bid/ask/mid for all tickers via refdata."""
    import blpapi

    if not session.openService("//blp/refdata"):
        print("ERROR: Cannot open //blp/refdata")
        return None

    svc = session.getService("//blp/refdata")
    req = svc.createRequest("ReferenceDataRequest")

    all_secs = {}
    for tenor, info in OIS_TICKERS.items():
        all_secs[info["sec"]] = ("OIS", tenor, info)
    for tenor, info in OFFSHORE_TICKERS.items():
        all_secs[info["sec"]] = ("OFF", tenor, info)
    all_secs[TLREF_TICKER] = ("TLREF", "ON", {})

    for sec in all_secs:
        req.getElement("securities").appendValue(sec)
    for f in FIELDS:
        req.getElement("fields").appendValue(f)

    session.sendRequest(req)

    results = {}
    while True:
        ev = session.nextEvent(5000)
        for msg in ev:
            if msg.hasElement("securityData"):
                sec_arr = msg.getElement("securityData")
                for i in range(sec_arr.numValues()):
                    sec_el = sec_arr.getValueAsElement(i)
                    sec_name = sec_el.getElementAsString("security")
                    fd = sec_el.getElement("fieldData")
                    bid = _safe(fd, "BID")
                    ask = _safe(fd, "ASK")
                    mid = _safe(fd, "MID")
                    results[sec_name] = {"bid": bid, "ask": ask, "mid": mid}
        if ev.eventType() == blpapi.Event.RESPONSE:
            break

    now = dt.datetime.now().isoformat(timespec="seconds")
    rows = []
    for sec, (curve, tenor, info) in all_secs.items():
        d = results.get(sec, {})
        rows.append({
            "timestamp": now,
            "curve": curve,
            "tenor": tenor,
            "ticker": sec,
            "bid": d.get("bid"),
            "ask": d.get("ask"),
            "mid": d.get("mid"),
        })

    return rows


def _safe(el, field):
    try:
        return el.getElementAsFloat(field)
    except Exception:
        return None


# ── Subscription mode ─────────────────────────────────────────────────

class TickHandler:
    """Handles real-time subscription updates."""
    def __init__(self):
        self.latest = {}
        self.changed = False

    def processEvent(self, event, _session):
        import blpapi
        if event.eventType() in (blpapi.Event.SUBSCRIPTION_DATA,
                                  blpapi.Event.SUBSCRIPTION_STATUS):
            for msg in event:
                topic = msg.correlationId().value()
                bid = _safe_msg(msg, "BID")
                ask = _safe_msg(msg, "ASK")
                mid = _safe_msg(msg, "MID")

                prev = self.latest.get(topic, {})
                if bid != prev.get("bid") or ask != prev.get("ask"):
                    self.changed = True
                    self.latest[topic] = {"bid": bid, "ask": ask, "mid": mid}
                    print(f"  [{dt.datetime.now().strftime('%H:%M:%S')}] {topic}: "
                          f"bid={bid} ask={ask} mid={mid}")


def _safe_msg(msg, field):
    try:
        return msg.getElementAsFloat(field)
    except Exception:
        return None


def run_subscription(session):
    """Subscribe to real-time bid/ask changes."""
    import blpapi

    handler = TickHandler()
    opts = blpapi.SessionOptions()
    opts.setServerHost("localhost")
    opts.setServerPort(8194)
    sub_session = blpapi.Session(opts, handler.processEvent)
    if not sub_session.start() or not sub_session.openService("//blp/mktdata"):
        print("ERROR: Cannot start subscription session")
        return

    subs = blpapi.SubscriptionList()
    all_secs = [info["sec"] for info in OIS_TICKERS.values()]
    all_secs += [info["sec"] for info in OFFSHORE_TICKERS.values()]
    all_secs.append(TLREF_TICKER)

    for sec in all_secs:
        subs.add(sec, "BID,ASK,MID", "", blpapi.CorrelationId(sec))

    sub_session.subscribe(subs)
    print(f"Subscribed to {len(all_secs)} tickers. Waiting for updates...")
    print("Press Ctrl+C to stop.\n")

    try:
        last_save = time.time()
        while True:
            time.sleep(1)
            # Save every 10 minutes or on change
            if handler.changed or (time.time() - last_save > 600):
                if handler.latest:
                    save_subscription_snapshot(handler.latest)
                    handler.changed = False
                    last_save = time.time()
    except KeyboardInterrupt:
        print("\nStopping subscription...")
    finally:
        sub_session.stop()


def save_subscription_snapshot(latest):
    """Save current subscription state to CSV."""
    now = dt.datetime.now().isoformat(timespec="seconds")
    rows = []

    for tenor, info in OIS_TICKERS.items():
        d = latest.get(info["sec"], {})
        rows.append({
            "timestamp": now, "curve": "OIS", "tenor": tenor,
            "ticker": info["sec"],
            "bid": d.get("bid"), "ask": d.get("ask"), "mid": d.get("mid"),
        })
    for tenor, info in OFFSHORE_TICKERS.items():
        d = latest.get(info["sec"], {})
        rows.append({
            "timestamp": now, "curve": "OFF", "tenor": tenor,
            "ticker": info["sec"],
            "bid": d.get("bid"), "ask": d.get("ask"), "mid": d.get("mid"),
        })
    d = latest.get(TLREF_TICKER, {})
    rows.append({
        "timestamp": now, "curve": "TLREF", "tenor": "ON",
        "ticker": TLREF_TICKER,
        "bid": d.get("bid"), "ask": d.get("ask"), "mid": d.get("mid"),
    })

    _append_csv(rows)
    print(f"  [SAVED] {now} — {len(rows)} rows")


# ── CSV I/O ───────────────────────────────────────────────────────────

FIELDNAMES = ["timestamp", "curve", "tenor", "ticker", "bid", "ask", "mid"]


def _append_csv(rows):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = OUTPUT_FILE.exists()
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_csv(rows):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# ── Poll mode ─────────────────────────────────────────────────────────

def run_poll(session, interval=600):
    """Poll every N seconds, append to CSV."""
    print(f"Polling every {interval}s. Press Ctrl+C to stop.\n")
    try:
        while True:
            rows = fetch_snapshot(session)
            if rows:
                _append_csv(rows)
                ts = rows[0]["timestamp"]
                ois_1y = next((r for r in rows if r["tenor"] == "1Y" and r["curve"] == "OIS"), None)
                off_1y = next((r for r in rows if r["tenor"] == "1Y" and r["curve"] == "OFF"), None)
                print(f"  [{ts}] OIS 1Y: {ois_1y['mid'] if ois_1y else 'N/A'}  "
                      f"OFF 1Y: {off_1y['mid'] if off_1y else 'N/A'}  "
                      f"({len(rows)} rows saved)")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopping poll...")


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Live Bloomberg OIS/Offshore feed")
    parser.add_argument("--subscribe", action="store_true",
                        help="Real-time subscription (updates on bid/ask change)")
    parser.add_argument("--once", action="store_true",
                        help="Single snapshot and exit")
    parser.add_argument("--interval", type=int, default=600,
                        help="Poll interval in seconds (default: 600 = 10 min)")
    args = parser.parse_args()

    session = init_session()

    if args.once:
        rows = fetch_snapshot(session)
        if rows:
            _write_csv(rows)
            print(f"Saved {len(rows)} rows to {OUTPUT_FILE}")
        session.stop()
    elif args.subscribe:
        run_subscription(session)
    else:
        run_poll(session, args.interval)
        session.stop()


if __name__ == "__main__":
    main()
