"""Scriptlerin ortak ayarları: klasörler, ligler ve sezon kodları."""
import sys
from datetime import date
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "model"))

VERI = KOK / "data"
TAHMIN = KOK / "tahminler"
RAPOR = KOK / "raporlar"

# football-data.co.uk kodu, klasör adı, API-Football lig numarası, geçmiş verinin başladığı sezon
LIGLER = {
    "super_lig":   {"kod": "T1", "klasor": VERI / "super_lig",   "api_id": 203, "ilk_sezon": 2013, "ad": "Süper Lig"},
    "premier_lig": {"kod": "E0", "klasor": VERI / "premier_lig", "api_id": 39,  "ilk_sezon": 2019, "ad": "Premier Lig"},
}


def guncel_sezon(bugun=None):
    """Sezon, başladığı yılla gösterilir: Kasım 2026 → 2026 (yani 2026-27)."""
    bugun = bugun or date.today()
    return bugun.year if bugun.month >= 7 else bugun.year - 1


def sezon_kodu(yil):
    """football-data.co.uk adres kodu: 2026 → '2627'."""
    return f"{yil % 100:02d}{(yil + 1) % 100:02d}"


def sezon_dosyasi(lig, yil):
    a = LIGLER[lig]
    return a["klasor"] / f"{a['kod']}_{yil}-{(yil + 1) % 100:02d}.csv"


def lig_dosyalari(lig):
    a = LIGLER[lig]
    return sorted(a["klasor"].glob(f"{a['kod']}_*.csv"))
