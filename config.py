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
DAY_CONV_X100 = 36_500          # 365 × 100  (yüzde → oran dönüşümü)
FIXED_CPN_PERIOD = 182          # Sabit kuponlu tahvil kupon periyodu (gün)
TLREF_CPN_PERIOD = 91           # TLREF tahvil kupon periyodu (gün)

# ═══════════════════════════════════════════════════════════════════
#  Bloomberg Ticker Listeleri
# ═══════════════════════════════════════════════════════════════════

# TLREF O/N referans oranı (ayrı çekilir — mid yerine last_price kullanılır)
BISTTREF_TICKER = "BISTTREF Index"

# Onshore OIS swap ticker'ları
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

# ═══════════════════════════════════════════════════════════════════
#  PPK Toplantı Tarihleri
# ═══════════════════════════════════════════════════════════════════

PPK_DATES = [
    date(2026, 4, 24),  date(2026, 6, 12),  date(2026, 7, 24),
    date(2026, 9, 11),  date(2026, 10, 23), date(2026, 12, 11),
    date(2027, 1, 22),  date(2027, 3, 19),  date(2027, 4, 24),
    date(2027, 6, 11),
]

# ═══════════════════════════════════════════════════════════════════
#  Türkiye Resmi Tatilleri (2025-2028)
# ═══════════════════════════════════════════════════════════════════

TR_HOLIDAYS: set[date] = {
    # 2025
    date(2025, 1, 1),  date(2025, 3, 30), date(2025, 3, 31),
    date(2025, 4, 1),  date(2025, 4, 23), date(2025, 5, 1),
    date(2025, 5, 19), date(2025, 6, 6),  date(2025, 6, 7),
    date(2025, 6, 8),  date(2025, 6, 9),  date(2025, 7, 15),
    date(2025, 8, 30), date(2025, 10, 29),
    # 2026
    date(2026, 1, 1),  date(2026, 3, 20), date(2026, 3, 21),
    date(2026, 3, 22), date(2026, 4, 23), date(2026, 5, 1),
    date(2026, 5, 19), date(2026, 5, 27), date(2026, 5, 28),
    date(2026, 5, 29), date(2026, 5, 30), date(2026, 7, 15),
    date(2026, 8, 30), date(2026, 10, 29),
    # 2027
    date(2027, 1, 1),  date(2027, 3, 9),  date(2027, 3, 10),
    date(2027, 3, 11), date(2027, 4, 23), date(2027, 5, 1),
    date(2027, 5, 16), date(2027, 5, 17), date(2027, 5, 18),
    date(2027, 5, 19), date(2027, 7, 15), date(2027, 8, 30),
    date(2027, 10, 29),
    # 2028
    date(2028, 1, 1),  date(2028, 2, 27), date(2028, 2, 28),
    date(2028, 2, 29), date(2028, 4, 23), date(2028, 5, 1),
    date(2028, 5, 5),  date(2028, 5, 6),  date(2028, 5, 7),
    date(2028, 5, 8),  date(2028, 5, 19), date(2028, 7, 15),
    date(2028, 8, 30), date(2028, 10, 29),
}

# ═══════════════════════════════════════════════════════════════════
#  Dosya Yolları
# ═══════════════════════════════════════════════════════════════════

OUTPUT_DIR = "output"
