"""
Merkezi Konfigürasyon
=====================
Sabitler, Bloomberg ticker'ları, PPK tarihleri, TR tatilleri.
"""
from datetime import date

# ═══════════════════════════════════════════════════════════════════
#  Day Count & Kupon Konvansiyonları
# ═══════════════════════════════════════════════════════════════════

DAY_CONV = 365                  # Onshore TRY: ACT/365
DAY_CONV_X100 = 36_500          # 365 × 100
FIXED_CPN_PERIOD = 182          # Sabit kuponlu tahvil kupon periyodu (gün)
TLREF_CPN_PERIOD = 91           # TLREF tahvil kupon periyodu (gün)

# ═══════════════════════════════════════════════════════════════════
#  Bloomberg Ticker Listeleri
# ═══════════════════════════════════════════════════════════════════

# TLREF O/N referans oranı
BISTTREF_TICKER = "BISTTREF Index"

# Onshore OIS swap ticker'ları (tenor, Bloomberg ticker)
ONSHORE_OIS_TICKERS = [
    ("1W",   "TYSO1Z GFOF Curncy"),
    ("1M",   "TYSOA GFOF Curncy"),
    ("2M",   "TYSOB GFOF Curncy"),
    ("3M",   "TYSOC GFOF Curncy"),
    ("6M",   "TYSOF GFOF Curncy"),
    ("9M",   "TYSOI GFOF Curncy"),
    ("1Y",   "TYSO1 GFOF Curncy"),
    ("18M",  "TYSO1F GFOF Curncy"),
    ("2Y",   "TYSO2 GFOF Curncy"),
    ("3Y",   "TYSO3 GFOF Curncy"),
    ("4Y",   "TYSO4 GFOF Curncy"),
    ("5Y",   "TYSO5 GFOF Curncy"),
    ("6Y",   "TYSO6 GFOF Curncy"),
    ("7Y",   "TYSO7 GFOF Curncy"),
    ("8Y",   "TYSO8 GFOF Curncy"),
    ("9Y",   "TYSO9 GFOF Curncy"),
    ("10Y",  "TYSO10 GFOF Curncy"),
]

# Offshore TRY deposit tickers (tenor, Bloomberg ticker, days-approx)
OFFSHORE_TRYI_TICKERS = [
    ("ON",   "TRYION Curncy",   0),
    ("TN",   "TRYITN Curncy",   1),
    ("1W",   "TRYI1W Curncy",   7),
    ("2W",   "TRYI2W Curncy",   14),
    ("1M",   "TRYI1M Curncy",   30),
    ("2M",   "TRYI2M Curncy",   63),
    ("3M",   "TRYI3M Curncy",   91),
    ("6M",   "TRYI6M Curncy",   183),
    ("9M",   "TRYI9M Curncy",   275),
    ("1Y",   "TRYI12M Curncy",  365),
    ("18M",  "TRYI18M Curncy",  548),
    ("2Y",   "TRYI2Y Curncy",   731),
    ("3Y",   "TRYI3Y Curncy",   1096),
]

# ═══════════════════════════════════════════════════════════════════
#  Tahvil ISIN Listesi (tek kolonluk config — fiyatlar BBG'den)
# ═══════════════════════════════════════════════════════════════════

# (ISIN, maturity_date, coupon_rate, freq, bond_type)
# freq: 0=ZCB, 2=semi, 4=quarterly
# bond_type: "zcb", "flt" (TLREF-linked), "fix"
BOND_UNIVERSE = [
    ("TRB170626T13", "2026-06-17", 0,     0, "zcb"),
    ("TRT080726T13", "2026-07-08", 42.35, 4, "flt"),
    ("TRT190826T19", "2026-08-19", 40.08, 4, "flt"),
    ("TRT060127T10", "2027-01-06", 0,     0, "zcb"),
    ("TRT130127T11", "2027-01-13", 39.90, 4, "flt"),
    ("TRT160627T13", "2027-06-16", 40.32, 4, "flt"),
    ("TRT140727T14", "2027-07-14", 37.84, 2, "fix"),
    ("TRT131027T10", "2027-10-13", 39.90, 4, "flt"),
    ("TRT131027T36", "2027-10-13", 36.78, 2, "fix"),
    ("TRD171127T13", "2027-11-17", 39.0,  2, "fix"),
    ("TRT190128T14", "2028-01-19", 39.82, 4, "flt"),
    ("TRT010328T12", "2028-03-01", 40.63, 4, "flt"),
    ("TRT170528T12", "2028-05-17", 40.08, 4, "flt"),
    ("TRT060928T11", "2028-09-06", 40.48, 4, "flt"),
    ("TRT081128T15", "2028-11-08", 31.08, 2, "fix"),
    ("TRT061228T16", "2028-12-06", 40.48, 4, "flt"),
    ("TRT070329T15", "2029-03-07", 40.48, 4, "flt"),
    ("TRT040729T14", "2029-04-07", 40.01, 2, "fix"),
    ("TRT130629T30", "2029-06-13", 40.32, 4, "flt"),
    ("TRT120929T12", "2029-09-12", 30.0,  2, "fix"),
    ("TRT090130T12", "2030-01-09", 37.2,  2, "fix"),
    ("TRT100730T13", "2030-07-10", 34.1,  2, "fix"),
]

# ═══════════════════════════════════════════════════════════════════
#  PPK Toplantı Tarihleri
# ═══════════════════════════════════════════════════════════════════

PPK_DATES = [
    date(2026, 4, 24),  date(2026, 6, 12),  date(2026, 7, 24),
    date(2026, 9, 11),  date(2026, 10, 23), date(2026, 12, 11),
    date(2027, 1, 22),  date(2027, 3, 19),  date(2027, 4, 24),
    date(2027, 6, 11),  date(2027, 7, 23),  date(2027, 9, 3),
    date(2027, 10, 15), date(2027, 11, 26),
    date(2028, 1, 7),   date(2028, 2, 18),  date(2028, 3, 31),
    date(2028, 5, 12),  date(2028, 6, 23),  date(2028, 8, 4),
    date(2028, 9, 15),  date(2028, 10, 27), date(2028, 12, 8),
    date(2029, 1, 19),  date(2029, 3, 2),   date(2029, 4, 13),
]

# ═══════════════════════════════════════════════════════════════════
#  Dosya Yolları
# ═══════════════════════════════════════════════════════════════════

OUTPUT_DIR = "output"

# ═══════════════════════════════════════════════════════════════════
#  Data Refresh
# ═══════════════════════════════════════════════════════════════════

POLLING_INTERVAL_SEC = 300   # 5 dakika fallback polling
