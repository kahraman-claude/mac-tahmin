"""
football-data.co.uk'tan güncel verileri indirir.
  - Her ligin devam eden sezonu her gün yeniden indirilir (yeni sonuçlar eklensin diye).
  - Klasörde olmayan eski sezonlar bir kez indirilir.
  - fixtures.csv: önümüzdeki maçlar ve bahis oranları (data/fixtures.csv).
Kullanım: python scripts/veri_indir.py
"""
import io
import sys
import urllib.request

import pandas as pd

from ortak import LIGLER, VERI, guncel_sezon, sezon_dosyasi, sezon_kodu

ADRES = "https://www.football-data.co.uk"


def indir(url):
    istek = urllib.request.Request(url, headers={"User-Agent": "mac-tahmin/1.0"})
    with urllib.request.urlopen(istek, timeout=60) as yanit:
        return yanit.read()


def gecerli_csv(icerik, kod=None):
    """İndirilen dosyanın gerçekten maç verisi olduğunu kontrol eder (hata sayfası değil)."""
    try:
        df = pd.read_csv(io.BytesIO(icerik), encoding="latin-1", on_bad_lines="skip")
    except Exception:
        return False
    if not {"HomeTeam", "AwayTeam"} <= set(df.columns):
        return False
    return kod is None or "Div" not in df.columns or (df["Div"].dropna() == kod).all()


def main():
    hata = 0
    simdi = guncel_sezon()
    for lig, a in LIGLER.items():
        for yil in range(a["ilk_sezon"], simdi + 1):
            hedef = sezon_dosyasi(lig, yil)
            if hedef.exists() and yil < simdi:
                continue                      # biten sezonlar değişmez
            url = f"{ADRES}/mmz4281/{sezon_kodu(yil)}/{a['kod']}.csv"
            try:
                icerik = indir(url)
            except Exception as e:
                print(f"UYARI: {url} indirilemedi: {e}"); hata += 1; continue
            if not gecerli_csv(icerik, a["kod"]):
                print(f"UYARI: {url} geçerli bir maç dosyası değil, atlandı"); hata += 1; continue
            hedef.write_bytes(icerik)
            print(f"{a['ad']} {yil}-{(yil + 1) % 100:02d}: indirildi ({len(icerik) // 1024} KB)")
    try:
        icerik = indir(f"{ADRES}/fixtures.csv")
        if gecerli_csv(icerik):
            (VERI / "fixtures.csv").write_bytes(icerik); print("fixtures.csv: indirildi")
    except Exception as e:
        print(f"UYARI: fixtures.csv indirilemedi: {e}"); hata += 1
    sys.exit(1 if hata and not (VERI / "fixtures.csv").exists() else 0)


if __name__ == "__main__":
    main()
