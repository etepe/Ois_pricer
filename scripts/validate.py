"""
Validate the OIS bootstrap engine against the Excel spreadsheet values.

Uses the hardcoded market data from the Excel (as of 2026-04-14 value date)
to verify bootstrap DFs and implied rates match.
"""

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine_v2 import (
    OISQuote, bootstrap, extract_implied_ppk, load_holidays,
    par_rate_from_dfs,
)
from engine_v2.calendar import add_business_days


def main():
    # ── Market data from Excel (as of trade date 2026-04-11 → VD 2026-04-14) ──
    # Excel shows VD = 2026-04-14, which is T+1 from trade date 2026-04-11 (Friday)
    # Actually 2026-04-13 is Sunday, 2026-04-14 is Monday
    # So trade date = 2026-04-11 (Friday), T+1 = 2026-04-14 (Monday) ✓

    trade_date = dt.date(2026, 4, 13)  # Monday; T+1 VD = April 14 (Tuesday)

    quotes = [
        OISQuote("1W",   0, 7,   39.60, 40.60, "1W"),
        OISQuote("2W",   0, 14,  39.60, 40.60, "2W"),
        OISQuote("1M",   1, 0,   39.00, 41.00, "1M"),
        OISQuote("2M",   2, 0,   40.00, 42.70, "2M"),
        OISQuote("3M",   3, 0,   40.30, 43.00, "3M"),
        OISQuote("6M",   6, 0,   38.60, 42.40, "6M"),
        OISQuote("9M",   9, 0,   37.40, 41.60, "9M"),
        OISQuote("1Y",  12, 0,   36.50, 40.70, "1Y"),
        OISQuote("18M", 18, 0,   35.00, 39.50, "18M"),
        OISQuote("2Y",  24, 0,   33.80, 38.56, "2Y"),
        OISQuote("3Y",  36, 0,   32.50, 36.62, "3Y"),
        OISQuote("4Y",  48, 0,   31.20, 35.34, "4Y"),
        OISQuote("5Y",  60, 0,   30.10, 34.32, "5Y"),
    ]

    hols = load_holidays()
    result = bootstrap(quotes, trade_date, "mid", hols)

    print(f"Trade date: {result.trade_date}")
    print(f"Value date: {result.value_date}")
    print()

    # ── Compare with Excel DFs ──
    # Excel values from standart_dates_and_prices sheet (AC column)
    excel_dfs = {
        "3M":  (91,  0.9059286202707113),
        "6M":  (183, 0.8243722982646123),
        "9M":  (275, 0.7536719649808972),
        "1Y":  (365, 0.6932977520588294),
        "18M": (548, 0.5894080854325402),
        "2Y":  (731, 0.5058783564010385),
        "3Y":  (1098, 0.3808753140426263),
    }

    print("=" * 70)
    print(f"{'Tenor':<6} {'Days':>5} {'Excel DF':>14} {'Engine DF':>14} {'Diff (bp)':>10}")
    print("-" * 70)

    for tenor, (days, excel_df) in excel_dfs.items():
        engine_df = result.get_df(days)
        diff_bp = (engine_df - excel_df) * 10000
        flag = " ⚠" if abs(diff_bp) > 5 else " ✓"
        print(f"{tenor:<6} {days:>5} {excel_df:>14.10f} {engine_df:>14.10f} {diff_bp:>+10.2f}{flag}")

    print()

    # ── Zero rates at nodes ──
    print("=" * 70)
    print(f"{'Tenor':<6} {'Days':>5} {'DF':>14} {'Zero Rate':>10}")
    print("-" * 70)
    for node in result.nodes:
        if node.days > 0:
            zr = result.zero_rate(node.days) * 100
            print(f"{node.tenor:<6} {node.days:>5} {node.df:>14.10f} {zr:>9.4f}%")

    print()

    # ── Implied PPK rates ──
    ppk_dates = [
        dt.date(2026, 4, 24), dt.date(2026, 6, 12), dt.date(2026, 7, 24),
        dt.date(2026, 9, 11), dt.date(2026, 10, 23), dt.date(2026, 12, 11),
        dt.date(2027, 1, 22), dt.date(2027, 3, 18), dt.date(2027, 4, 26),
        dt.date(2027, 6, 11), dt.date(2027, 7, 23), dt.date(2027, 9, 3),
    ]

    implied = extract_implied_ppk(result, ppk_dates)

    print("=" * 70)
    print(f"{'PPK Date':<12} {'Period':>6} {'Implied Rate':>13} {'Chg':>8} {'DF':>14}")
    print("-" * 70)

    prev_rate = 40.10  # approximate current TLREF mid
    for p in implied:
        chg = p.implied_rate_pct - prev_rate
        chg_str = f"{chg:+.0f} bp" if abs(chg) > 0.05 else "  —"
        print(
            f"{p.date.isoformat():<12} {p.period_days:>4}d  "
            f"{p.implied_rate_pct:>11.2f}%  {chg_str:>8}  {p.df:>14.10f}"
        )
        prev_rate = p.implied_rate_pct

    print()

    # ── Verify par rates round-trip ──
    print("=" * 70)
    print("Par rate round-trip (should match input mid rates):")
    print(f"{'Tenor':<6} {'Input Mid':>10} {'Computed':>10} {'Diff (bp)':>10}")
    print("-" * 70)

    for q in quotes:
        computed = par_rate_from_dfs(
            result.value_date, q.months, q.days, result.nodes, hols
        )
        diff = computed - q.mid
        flag = " ⚠" if abs(diff) > 0.05 else " ✓"
        print(f"{q.tenor:<6} {q.mid:>9.2f}% {computed:>9.2f}% {diff*100:>+10.2f}{flag}")

    print()
    print("[Done]")


if __name__ == "__main__":
    main()
