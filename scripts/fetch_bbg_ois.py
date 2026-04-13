"""
Bloomberg Historical OIS Data Fetcher
=====================================

One-time script to fetch historical TLREF OIS quotes from Bloomberg.
Saves to data/ois_history.csv. If the file already exists, skips.

Usage:
    python scripts/fetch_bbg_ois.py [--force] [--start 2024-01-01] [--end 2026-04-14]

Requirements:
    - Bloomberg Terminal running (or BPIPE connection)
    - blpapi Python package: pip install blpapi

Tickers (BGN source for most, GFOF for 1W/2W):
    1W:  TYSO1Z GFOF Curncy
    2W:  TYSO2Z GFOF Curncy
    1M:  TYSOA  GFOF Curncy
    2M:  TYSOB  GFOF Curncy
    3M:  TYSOC  GFOF Curncy
    6M:  TYSOF  GFOF Curncy
    9M:  TYSOI  GFOF Curncy
    1Y:  TYSO1  GFOF Curncy
    18M: TYSO1F GFOF Curncy
    2Y:  TYSO2  GFOF Curncy
    3Y:  TYSO3  GFOF Curncy
    4Y:  TYSO4  GFOF Curncy
    5Y:  TYSO5  GFOF Curncy
"""

import argparse
import datetime as dt
import sys
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_FILE = DATA_DIR / "ois_history.csv"

OIS_TICKERS = {
    "1W":  {"ticker": "TYSO1Z GFOF Curncy", "months": 0,  "days": 7},
    "2W":  {"ticker": "TYSO2Z GFOF Curncy", "months": 0,  "days": 14},
    "1M":  {"ticker": "TYSOA GFOF Curncy",  "months": 1,  "days": 0},
    "2M":  {"ticker": "TYSOB GFOF Curncy",  "months": 2,  "days": 0},
    "3M":  {"ticker": "TYSOC GFOF Curncy",  "months": 3,  "days": 0},
    "6M":  {"ticker": "TYSOF GFOF Curncy",  "months": 6,  "days": 0},
    "9M":  {"ticker": "TYSOI GFOF Curncy",  "months": 9,  "days": 0},
    "1Y":  {"ticker": "TYSO1 GFOF Curncy",  "months": 12, "days": 0},
    "18M": {"ticker": "TYSO1F GFOF Curncy", "months": 18, "days": 0},
    "2Y":  {"ticker": "TYSO2 GFOF Curncy",  "months": 24, "days": 0},
    "3Y":  {"ticker": "TYSO3 GFOF Curncy",  "months": 36, "days": 0},
    "4Y":  {"ticker": "TYSO4 GFOF Curncy",  "months": 48, "days": 0},
    "5Y":  {"ticker": "TYSO5 GFOF Curncy",  "months": 60, "days": 0},
}

# Fields to fetch
FIELDS = ["PX_BID", "PX_ASK", "PX_MID"]

# ── Bloomberg API wrapper ─────────────────────────────────────────────

def fetch_historical_data(
    tickers: dict,
    fields: list,
    start_date: dt.date,
    end_date: dt.date,
) -> list[dict]:
    """
    Fetch historical data from Bloomberg using blpapi.
    Returns list of dicts: {date, tenor, ticker, bid, ask, mid}
    """
    try:
        import blpapi
    except ImportError:
        print("ERROR: blpapi not installed. Run: pip install blpapi")
        print("Also ensure Bloomberg Terminal is running.")
        sys.exit(1)

    session_options = blpapi.SessionOptions()
    session_options.setServerHost("localhost")
    session_options.setServerPort(8194)

    session = blpapi.Session(session_options)
    if not session.start():
        print("ERROR: Failed to start Bloomberg session.")
        print("Ensure Bloomberg Terminal is running.")
        sys.exit(1)

    if not session.openService("//blp/refdata"):
        print("ERROR: Failed to open //blp/refdata service.")
        session.stop()
        sys.exit(1)

    refdata = session.getService("//blp/refdata")
    results = []

    for tenor, info in tickers.items():
        ticker = info["ticker"]
        print(f"  Fetching {tenor} ({ticker})...", end=" ", flush=True)

        request = refdata.createRequest("HistoricalDataRequest")
        request.getElement("securities").appendValue(ticker)
        for f in fields:
            request.getElement("fields").appendValue(f)
        request.set("startDate", start_date.strftime("%Y%m%d"))
        request.set("endDate", end_date.strftime("%Y%m%d"))
        request.set("periodicitySelection", "DAILY")
        request.set("nonTradingDayFillOption", "NON_TRADING_WEEKDAYS")
        request.set("nonTradingDayFillMethod", "PREVIOUS_VALUE")

        session.sendRequest(request)

        count = 0
        while True:
            event = session.nextEvent(5000)
            for msg in event:
                if msg.hasElement("securityData"):
                    sec_data = msg.getElement("securityData")
                    if sec_data.hasElement("fieldData"):
                        field_data = sec_data.getElement("fieldData")
                        for i in range(field_data.numValues()):
                            row = field_data.getValueAsElement(i)
                            d = row.getElementAsDatetime("date")
                            trade_date = dt.date(d.year, d.month, d.day)

                            bid = _safe_float(row, "PX_BID")
                            ask = _safe_float(row, "PX_ASK")
                            mid = _safe_float(row, "PX_MID")

                            results.append({
                                "trade_date": trade_date.isoformat(),
                                "tenor": tenor,
                                "ticker": ticker,
                                "months": info["months"],
                                "days": info["days"],
                                "bid": bid,
                                "ask": ask,
                                "mid": mid,
                            })
                            count += 1

            if event.eventType() == blpapi.Event.RESPONSE:
                break

        print(f"{count} rows")

    session.stop()
    return results


def _safe_float(element, field_name):
    """Safely extract float from Bloomberg element."""
    try:
        return element.getElementAsFloat(field_name)
    except Exception:
        return None


# ── Value date computation ────────────────────────────────────────────

def compute_value_dates(rows: list[dict]) -> list[dict]:
    """
    Compute T+1 value dates for each trade date.
    Uses the holidays engine for proper BD adjustment.
    """
    sys.path.insert(0, str(PROJECT_ROOT))
    from engine_v2.calendar import load_holidays, add_business_days

    hols = load_holidays()

    for row in rows:
        td = dt.date.fromisoformat(row["trade_date"])
        vd = add_business_days(td, 1, hols)
        row["value_date"] = vd.isoformat()

    return rows


# ── CSV I/O ───────────────────────────────────────────────────────────

def save_csv(rows: list[dict], filepath: Path):
    """Save results to CSV."""
    import csv

    filepath.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "trade_date", "value_date", "tenor", "ticker",
        "months", "days", "bid", "ask", "mid",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    print(f"\n[OK] Saved {len(rows)} rows to {filepath}")


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fetch TLREF OIS historical data from Bloomberg")
    parser.add_argument("--force", action="store_true", help="Re-fetch even if CSV exists")
    parser.add_argument("--start", default="2024-01-02", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="End date (default: today)")
    args = parser.parse_args()

    if OUTPUT_FILE.exists() and not args.force:
        print(f"[SKIP] {OUTPUT_FILE} already exists. Use --force to re-fetch.")
        return

    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end) if args.end else dt.date.today()

    print(f"Fetching TLREF OIS data: {start} → {end}")
    print(f"Tickers: {len(OIS_TICKERS)}")
    print()

    rows = fetch_historical_data(OIS_TICKERS, FIELDS, start, end)

    print(f"\nComputing T+1 value dates...")
    rows = compute_value_dates(rows)

    save_csv(rows, OUTPUT_FILE)


if __name__ == "__main__":
    main()
