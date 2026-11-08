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


# Web sayfasında gösterilecek takım adları (veri dosyalarındaki kısaltmalar → tam ad)
TAKIM_ADI = {
    # Süper Lig
    "Besiktas": "Beşiktaş", "Buyuksehyr": "Başakşehir", "Corum": "Çorum FK", "Eyupspor": "Eyüpspor",
    "Fenerbahce": "Fenerbahçe", "Gaziantep": "Gaziantep FK", "Genclerbirligi": "Gençlerbirliği",
    "Goztep": "Göztepe", "Kasimpasa": "Kasımpaşa", "Ad. Demirspor": "Adana Demirspor",
    "Ankaragucu": "Ankaragücü", "Hatayspor": "Hatayspor", "Istanbulspor": "İstanbulspor",
    "Karagumruk": "Karagümrük", "Pendikspor": "Pendikspor", "Umraniyespor": "Ümraniyespor",
    "Bodrumspor": "Bodrumspor", "Sivasspor": "Sivasspor", "Kayserispor": "Kayserispor",
    "Antalyaspor": "Antalyaspor", "Hatayspor": "Hatayspor",
    # Premier Lig
    "Man City": "Manchester City", "Man United": "Manchester United", "Nott'm Forest": "Nottingham Forest",
    "Hull": "Hull City", "Ipswich": "Ipswich Town", "Leeds": "Leeds United", "Newcastle": "Newcastle United",
    "Coventry": "Coventry City", "Tottenham": "Tottenham Hotspur", "Wolves": "Wolverhampton",
    "West Ham": "West Ham United", "Sheffield United": "Sheffield United", "Leicester": "Leicester City",
}


def takim_adi(t):
    return TAKIM_ADI.get(t, t)
