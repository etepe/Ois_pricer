# TLREF OIS Pricer

Onshore TRY OIS curve bootstrap, implied PPK (MPC) rate extraction, and scenario analysis engine.

## Architecture

```
Ois_pricer/
├── engine_v2/                  ← New: validated bootstrap engine
│   ├── calendar.py             Turkish holiday calendar (auto-cached)
│   └── bootstrap.py            Sequential quarterly bootstrap, implied PPK
│
├── scripts/
│   ├── fetch_bbg_ois.py        Bloomberg historical OIS data fetcher
│   └── validate.py             Excel cross-validation (0.00 bp match)
│
├── frontend/
│   └── tlref-ois-pricer.jsx    React interactive pricer (runs on claude.ai)
│
├── data/
│   └── tr_holidays.json        Cached Turkish holiday calendar (2020-2035)
│
├── engine.py                   Legacy v1 engine
├── config.py                   Tickers, constants, PPK dates
├── data_provider.py            Bloomberg + Mock provider abstraction
├── web.py                      Flask web UI
├── main.py                     CLI orchestration
├── static/index.html           Legacy web frontend
└── tests/
    └── test_bootstrap.py       Grid and par rate verification
```

## Bootstrap Engine v2

### Conventions
- **Day count**: Act/365 (Turkish OIS standard)
- **Settlement**: T+1
- **Payment frequency**: Quarterly (3M) for tenors > 3M
- **Interpolation**: Log-linear on discount factors (not linear on rates)
- **Holiday calendar**: `holidays` Python package (Turkish public holidays)

### Method

**Short end** (≤ 3M): Zero-coupon simple discount

```
DF = 1 / (1 + r × d / 365)
```

**Long end** (> 3M): Sequential quarterly grid bootstrap

1. Generate quarterly nodes: 3M, 6M, 9M, 12M, 15M, 18M, ...
2. Linearly interpolate par swap rates for intermediate points (e.g. 15M from 1Y and 18M market quotes)
3. Bootstrap sequentially — each node solves for its DF using all previously computed DFs:

```
DF_n = (1 − r_n × Σ(τ_i × DF_i) / 365) / (1 + r_n × τ_n / 365)
```

### Validation

All DFs match the reference Excel to 10 decimal places. Par rate round-trip is exact (0.00 bp) for all tenors.

```
$ python scripts/validate.py

Tenor   Days       Excel DF      Engine DF  Diff (bp)
3M        91   0.9059286203   0.9059286203      +0.00 ✓
6M       183   0.8243722983   0.8243722983      +0.00 ✓
9M       275   0.7536719650   0.7536719650      +0.00 ✓
1Y       365   0.6932977521   0.6932977521      +0.00 ✓
18M      548   0.5894080854   0.5894080854      +0.00 ✓
2Y       731   0.5058783564   0.5058783564      +0.00 ✓
3Y      1098   0.3808753140   0.3808753140      +0.00 ✓
```

## Setup

```bash
pip install -r requirements.txt

# Bloomberg (work machine only):
pip install blpapi
```

## Usage

### Implied PPK Rates
```python
from engine_v2 import bootstrap, extract_implied_ppk, OISQuote
import datetime as dt

quotes = [
    OISQuote("1W",  0, 7,  39.60, 40.60),
    OISQuote("3M",  3, 0,  40.30, 43.00),
    OISQuote("6M",  6, 0,  38.60, 42.40),
    OISQuote("1Y", 12, 0,  36.50, 40.70),
    # ...
]

result = bootstrap(quotes, trade_date=dt.date(2026, 4, 13), quote_type="mid")

ppk_dates = [dt.date(2026,4,24), dt.date(2026,6,12), ...]
implied = extract_implied_ppk(result, ppk_dates)

for p in implied:
    print(f"{p.date}  {p.implied_rate_pct:.2f}%  DF={p.df:.6f}")
```

### Bloomberg Historical Data
```bash
# First run: fetches and saves to data/ois_history.csv
python scripts/fetch_bbg_ois.py --start 2024-01-02

# Subsequent runs: skips if file exists
python scripts/fetch_bbg_ois.py          # → [SKIP]
python scripts/fetch_bbg_ois.py --force  # → re-fetch
```

### Interactive React Pricer
The `frontend/tlref-ois-pricer.jsx` runs as an artifact on claude.ai with three tabs:
- **Implied PPK Rates** — forward rates between PPK meetings
- **Scenario Analysis** — apply bp deviations, see spot rate impact
- **Market Data** — editable bid/ask, bootstrapped zero curve

## Corrections Applied to Reference Excel

1. **Forward rate day count**: Fixed Act/360 → Act/365
2. **DF interpolation**: Replaced linear par rate interpolation with log-linear DF interpolation
3. **Settlement**: Confirmed T+1 (matching Excel WORKDAY formula)
4. **Quarterly grid**: Sequential bootstrap at every 3M node with par rate interpolation for missing tenors

---
*FETM RESEARCH*
