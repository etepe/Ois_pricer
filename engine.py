"""
Hesaplama Motoru
================
Onshore OIS eğrisi bootstrap, TLREF spread, implied PPK beklentisi.

Bootstrap Mantığı (Onshore — ACT/365):
    
    Tarih Gridi (44 satır, index 0–43):
        Row  0:  bugün                                      (df = 1)
        Row  1:  bugün + 1BD                                (O/N)
        Row  2:  bugün + 1W + 1BD                           (1W)
        Row  3:  bugün + 1M + 1BD                           (1M)
        Row  4:  bugün + 3M + 1BD                           (3M)   ← ilk quarterly node
        Row  5:  bugün + 6M + 1BD                           (6M)   ← bootstrap başlangıcı
        ...
        Row 43:  bugün + 120M + 1BD                         (10Y)

    Bölge 2 (kısa vade, DTM ≤ 3M):
        df = 1 / (1 + rate × DTM / 36500)
        SumProduct[i+1] = df[i] × DTM[i]        ← overwrite, NOT accumulate

    Bölge 3 (uzun vade, 6M → 10Y, iteratif swap bootstrap):
        df[n] = (1 − S × SumProduct[n] / 36500) / (1 + S × period[n] / 36500)
        SumProduct[n+1] = SumProduct[n] + df[n] × period[n]
"""
import calendar
import logging
from datetime import date, timedelta

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from config import DAY_CONV_X100, TLREF_CPN_PERIOD
from data_provider import OISMarketData, is_business_day, next_bday, add_bdays

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
#  Tarih Yardımcıları
# ═══════════════════════════════════════════════════════════════════

def _add_months(start: date, months: int) -> date:
    """Tarihe ay ekler. Ay sonu taşmasını yönetir (31 Oca + 1M → 28 Şub)."""
    m = start.month - 1 + months
    y = start.year + m // 12
    m = m % 12 + 1
    max_day = calendar.monthrange(y, m)[1]
    return date(y, m, min(start.day, max_day))


def _onshore_date(today: date, months: int = 0, weeks: int = 0) -> date:
    """
    Onshore tarih konvansiyonu:
        DateOffset(months/weeks) + CustomBusinessDay(1)
    Önce ay/hafta eklenir, sonra 1 iş günü ilerletilir.
    """
    if weeks > 0:
        raw = today + timedelta(weeks=weeks)
    elif months > 0:
        raw = _add_months(today, months)
    else:
        return today
    return add_bdays(raw, 1)


# ═══════════════════════════════════════════════════════════════════
#  1) ONSHORE OIS BOOTSTRAP
# ═══════════════════════════════════════════════════════════════════

# Grid tanımı: (label, months, weeks)
# Row 0  = bugün
# Row 1  = O/N (özel: bugün + 1BD)
# Row 2  = 1W
# Row 3  = 1M
# Row 4  = 3M   (quarterly grid başlangıcı)
# Row 5  = 6M
# ...
# Row 43 = 120M (10Y)
_GRID_SHORT = [
    ("T",    0,  0),   # Row 0: bugün
    ("O/N",  0,  0),   # Row 1: bugün + 1BD
    ("1W",   0,  1),   # Row 2: bugün + 1W + 1BD
    ("1M",   1,  0),   # Row 3: bugün + 1M + 1BD
]

# Row 4–43: her 3 ayda bir → 3, 6, 9, 12, 15, ..., 120
_GRID_QUARTERLY_MONTHS = list(range(3, 121, 3))  # 40 nokta → toplam 44 satır


def build_onshore_grid(today: date) -> pd.DataFrame:
    """
    44 satırlık onshore OIS tarih gridini oluşturur.
    
    Returns:
        DataFrame [label, date, DTM, period]
    """
    labels = []
    dates = []

    # ── Kısa vade (Row 0–3) ──
    for label, months, weeks in _GRID_SHORT:
        if label == "T":
            d = today
        elif label == "O/N":
            d = add_bdays(today, 1)
        else:
            d = _onshore_date(today, months=months, weeks=weeks)
        labels.append(label)
        dates.append(d)

    # ── Quarterly grid (Row 4–43) ──
    for m in _GRID_QUARTERLY_MONTHS:
        d = _onshore_date(today, months=m)
        y = m // 12
        rem = m % 12
        if rem == 0:
            labels.append(f"{y}Y")
        else:
            labels.append(f"{m}M")
        dates.append(d)

    # ── DTM ve Period hesapla ──
    dtm = [(d - today).days for d in dates]

    # Period:
    #   Row 0: 0
    #   Row 1–4 (Bölge 2): period = DTM  (kısa vade — swap'ta tek ödeme)
    #   Row 5+ (Bölge 3): period = date[n] - date[n-1]  (quarterly aralık)
    period = [0]  # Row 0
    for i in range(1, len(dates)):
        if i <= 4:
            # Bölge 2: kısa vade, period = DTM
            period.append(dtm[i])
        else:
            # Bölge 3: ardışık quarterly noktalar arası fark
            period.append((dates[i] - dates[i - 1]).days)

    return pd.DataFrame({
        "label": labels,
        "date": dates,
        "DTM": dtm,
        "period": period,
    })


def bootstrap_onshore(market: OISMarketData) -> pd.DataFrame:
    """
    Onshore OIS eğrisini bootstrap eder.
    
    Args:
        market: OISMarketData (today, bisttref_rate, tickers DataFrame)
    
    Returns:
        DataFrame [label, date, DTM, period, spot_ois, df, SumProduct]
        44 satır (index 0 = bugün, index 43 = 10Y)
    """
    today = market.today
    grid = build_onshore_grid(today)
    n = len(grid)

    # ── Market rate'leri DTM uzayına dönüştür ──
    # BISTTREF: O/N referans (maturity = bugün + 1BD)
    on_maturity = add_bdays(today, 1)
    on_dtm = (on_maturity - today).days  # = 1

    mkt_dtm = np.array([on_dtm] + [(m - today).days for m in market.tickers["maturity"]])
    mkt_mid = np.array([market.bisttref_rate] + list(market.tickers["mid"]))

    # ── Grid noktalarına lineer interpolasyon ──
    grid_dtm = grid["DTM"].values.astype(float)
    grid["spot_ois"] = np.interp(grid_dtm, mkt_dtm, mkt_mid)

    # ── Discount Factor Bootstrap ──
    df_arr = np.ones(n, dtype=float)
    sp_arr = np.zeros(n, dtype=float)  # SumProduct

    for i in range(1, n):
        dtm_i = grid_dtm[i]
        rate_i = grid.at[i, "spot_ois"]
        period_i = float(grid.at[i, "period"])

        if i <= 4:
            # ┌──────────────────────────────────────────────┐
            # │  BÖLGE 2: Kısa vade (O/N, 1W, 1M, 3M)      │
            # │  Basit faiz discount factor:                 │
            # │    df = 1 / (1 + rate × DTM / 36500)        │
            # │                                              │
            # │  SumProduct: bir sonraki satır için hazırla  │
            # │    SumProduct[i+1] = df[i] × DTM[i]         │
            # │    (overwrite — accumulate DEĞİL)            │
            # └──────────────────────────────────────────────┘
            df_arr[i] = 1.0 / (1.0 + rate_i * dtm_i / DAY_CONV_X100)

            if i < n - 1:
                sp_arr[i + 1] = df_arr[i] * dtm_i

        else:
            # ┌──────────────────────────────────────────────────────┐
            # │  BÖLGE 3: Uzun vade (6M → 10Y, iteratif bootstrap)  │
            # │                                                      │
            # │  Swap par rate denklemi:                             │
            # │    S × Σ(df[j]×period[j])/36500 + df[n]×(1+S×Δ/36500) = 1 │
            # │                                                      │
            # │  Çözüm:                                              │
            # │    df[n] = (1 − S×SumProduct[n]/36500)               │
            # │          / (1 + S×period[n]/36500)                   │
            # │                                                      │
            # │  SumProduct güncelleme (accumulate):                 │
            # │    SumProduct[n+1] = SumProduct[n] + df[n]×period[n] │
            # └──────────────────────────────────────────────────────┘
            df_arr[i] = (
                (1.0 - rate_i * sp_arr[i] / DAY_CONV_X100)
                / (1.0 + rate_i * period_i / DAY_CONV_X100)
            )

            # Son satır (10Y, index 43) hariç SumProduct güncelle
            if i < n - 1:
                sp_arr[i + 1] = sp_arr[i] + df_arr[i] * period_i

    grid["df"] = df_arr
    grid["SumProduct"] = sp_arr

    log.info(
        f"OIS bootstrap tamamlandı: {n} grid noktası, "
        f"O/N={grid.at[1, 'spot_ois']:.2f}%, "
        f"10Y df={df_arr[-1]:.6f}"
    )

    return grid


# ═══════════════════════════════════════════════════════════════════
#  2) TLREF SPREAD HESAPLAMA
# ═══════════════════════════════════════════════════════════════════

def _interp_df(t: float, ois_dtm: np.ndarray, ois_gross_up: np.ndarray,
               spread: float = 0.0) -> float:
    """
    OIS eğrisinden interpolasyon ile discount factor hesaplar.
    
    İnterpolasyon 1/df (gross-up factor) uzayında yapılır.
    Spread, df'ye paralel shift olarak uygulanır:
        df_shifted = df + spread
        1/df_shifted = 1/(df + spread)
        
    Pratikte: gross_up_shifted = gross_up uzayında interp,
    sonra spread düzeltmesi.
    """
    # 1/df uzayında interpolasyon (spread = 0 durumu)
    gross_up_at_t = np.interp(t, ois_dtm, ois_gross_up)
    df_at_t = 1.0 / gross_up_at_t

    # Spread uygula: df_shifted = df + spread
    df_shifted = df_at_t + spread
    if df_shifted <= 0:
        return 1e-10  # sıfıra bölme koruması
    return df_shifted


def _interp_pure_df(t: float, ois_dtm: np.ndarray, ois_gross_up: np.ndarray) -> float:
    """Saf OIS df (spread yok) — forward kupon hesabında kullanılır."""
    return 1.0 / np.interp(t, ois_dtm, ois_gross_up)


def _tlref_model_dirty(spread: float, dt_next_cpn: int, dtm: int,
                        ois_dtm: np.ndarray, ois_gross_up: np.ndarray) -> float:
    """
    TLREF tahvilin model dirty price'ı.
    
    Kuponlar 91 günlük periyotlarla, forward rate ile belirlenir.
    ⚠️ Forward kupon: saf OIS df ile (spread UYGULANMAZ)
    ⚠️ İskontolama: spread uygulanmış df ile
    """
    pv = 0.0
    t = dt_next_cpn

    while t <= dtm:
        # ── Forward kupon (saf OIS — spread yok) ──
        df_t = _interp_pure_df(t, ois_dtm, ois_gross_up)
        t_prev = max(t - TLREF_CPN_PERIOD, 0)
        df_t_prev = _interp_pure_df(t_prev, ois_dtm, ois_gross_up)
        forward_cpn = (df_t_prev / df_t - 1.0) * 100.0

        # ── İskonto (spread uygulanır) ──
        disc = _interp_df(t, ois_dtm, ois_gross_up, spread)
        pv += disc * forward_cpn

        # ── Vade tarihinde anapara ──
        if t == dtm:
            pv += disc * 100.0

        t += TLREF_CPN_PERIOD

    return pv


def calc_tlref_spread(spot_dirty: float, dt_next_cpn: int, dtm: int,
                       ois_base: pd.DataFrame) -> float:
    """
    TLREF tahvili için OIS spread hesaplar.
    
    Args:
        spot_dirty: Piyasa dirty fiyatı (TLREF'te px_last = dirty)
        dt_next_cpn: Sonraki kupona kalan gün (DTM % 91, 0 ise 91 kullan)
        dtm: Vadeye kalan gün
        ois_base: Bootstrap edilmiş OIS eğrisi [DTM, df]
    
    Returns:
        Spread (basis points). Pozitif = ucuz, negatif = pahalı.
    """
    ois_dtm = ois_base["DTM"].values.astype(float)
    ois_gross_up = (1.0 / ois_base["df"].values).astype(float)

    def price_diff(spread):
        model = _tlref_model_dirty(spread, dt_next_cpn, dtm, ois_dtm, ois_gross_up)
        return spot_dirty - model

    try:
        spread = brentq(price_diff, -0.1, 0.1, xtol=1e-10, maxiter=200)
        return round(-spread * 10_000, 1)  # basis points
    except (ValueError, RuntimeError):
        log.warning(f"Spread bulunamadı: DTM={dtm}, dirty={spot_dirty}")
        return float("nan")


def analyze_tlref_bonds(bonds_df: pd.DataFrame, ois_base: pd.DataFrame,
                         today: date) -> pd.DataFrame:
    """
    TLREF tahvil listesi için OIS spread hesaplar.
    
    Args:
        bonds_df: [isin, maturity, px_last]
        ois_base: Bootstrap edilmiş OIS eğrisi
        today: Bugünün tarihi
    """
    results = []
    for _, row in bonds_df.iterrows():
        mat = row["maturity"]
        if isinstance(mat, str):
            mat = pd.Timestamp(mat).date()
        elif isinstance(mat, pd.Timestamp):
            mat = mat.date()

        dtm = (mat - today).days
        dt_next_cpn = dtm % TLREF_CPN_PERIOD
        if dt_next_cpn == 0:
            dt_next_cpn = TLREF_CPN_PERIOD

        spread = calc_tlref_spread(
            spot_dirty=float(row["px_last"]),
            dt_next_cpn=dt_next_cpn,
            dtm=dtm,
            ois_base=ois_base,
        )

        results.append({
            "isin": row["isin"],
            "maturity": mat,
            "DTM": dtm,
            "dt_next_cpn": dt_next_cpn,
            "px_last": float(row["px_last"]),
            "ois_spread_bps": spread,
        })

    return pd.DataFrame(results)


# ═══════════════════════════════════════════════════════════════════
#  3) IMPLIED MPC BEKLENTİSİ
# ═══════════════════════════════════════════════════════════════════

def calc_implied_mpc(ppk_dates: list[date], ois_base: pd.DataFrame,
                      today: date) -> pd.DataFrame:
    """
    PPK toplantı tarihleri arasındaki implied forward rate ve
    implied MPC kararını hesaplar.
    
    DTM, spot date'e göre hesaplanır (T+1).
    
    Forward rate (günlük bileşik):
        BREF_rt = (gross_up(DTM[i]) / gross_up(DTM[i-1]))^(1/period) − 1) × 36500
    
    Implied MPC (basit faiz eşdeğeri):
        mpc = ((1 + BREF_rt/36500)^period − 1) / period × 36500
    """
    spot = add_bdays(today, 1)

    ois_dtm = ois_base["DTM"].values.astype(float)
    ois_gross_up = (1.0 / ois_base["df"].values).astype(float)

    results = []
    prev_dtm = 0
    prev_gu = 1.0  # spot noktasında df = 1 → gross_up = 1

    for ppk_date in ppk_dates:
        if ppk_date <= spot:
            continue

        dtm = (ppk_date - spot).days
        gu = float(np.interp(dtm, ois_dtm, ois_gross_up))

        period = dtm - prev_dtm
        if period <= 0:
            continue

        # Forward rate (günlük bileşik, yıllık %)
        fwd = ((gu / prev_gu) ** (1.0 / period) - 1.0) * DAY_CONV_X100

        # Implied MPC (basit faiz eşdeğeri, yıllık %)
        mpc = ((1.0 + fwd / DAY_CONV_X100) ** period - 1.0) / period * DAY_CONV_X100

        results.append({
            "ppk_date": ppk_date,
            "DTM_from_spot": dtm,
            "period_days": period,
            "forward_rate": round(fwd, 2),
            "implied_mpc": round(mpc, 2),
        })

        prev_dtm = dtm
        prev_gu = gu

    return pd.DataFrame(results)
