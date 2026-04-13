# OIS Pricer

Onshore TRY OIS eğrisi bootstrap, TLREF tahvil spread hesaplama ve implied PPK beklentisi.

## Mimari

```
Ois_pricer/
├── config.py           Sabitler, ticker'lar, tatiller, PPK tarihleri
├── data_provider.py    Bloomberg (blpapi) + MockProvider abstraction
├── engine.py           OIS bootstrap, TLREF spread, implied MPC
├── main.py             Orkestrasyon
├── requirements.txt
└── tests/
    └── test_bootstrap.py   44 noktalı grid ve swap par rate doğrulaması
```

## Kurulum

```bash
pip install -r requirements.txt

# Bloomberg bağlantısı için (şirkette):
pip install blpapi
```

## Kullanım

```bash
# Mock data ile test:
python main.py --mock

# Bloomberg ile (Terminal açık olmalı):
python main.py

# Doğrulama testleri:
python tests/test_bootstrap.py
```

## Bootstrap Detayları

### Tarih Gridi (44 satır)

| Row | Tenor | Konvansiyon |
|-----|-------|-------------|
| 0 | T (bugün) | — |
| 1 | O/N | bugün + 1BD |
| 2 | 1W | bugün + 1W + 1BD |
| 3 | 1M | bugün + 1M + 1BD |
| 4 | 3M | bugün + 3M + 1BD (ilk quarterly node) |
| 5–43 | 6M → 10Y | bugün + nM + 1BD (her 3 ayda bir) |

### Bölge 2 — Kısa Vade (Row 1–4)
```
df = 1 / (1 + rate × DTM / 36500)
SumProduct[i+1] = df[i] × DTM[i]       ← overwrite
```

### Bölge 3 — Uzun Vade (Row 5–43)
```
df[n] = (1 − S × SumProduct[n] / 36500) / (1 + S × period[n] / 36500)
SumProduct[n+1] = SumProduct[n] + df[n] × period[n]    ← accumulate
```

### Doğrulama
Swap par rate her noktada `|fixed − float| < 1e-16` hassasiyetle yeniden üretilir.
