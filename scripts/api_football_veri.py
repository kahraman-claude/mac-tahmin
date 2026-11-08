"""
API-Football'dan veri çeker (anahtar varsa). Şimdilik iki komut:
  kontrol : anahtar çalışıyor mu, hangi sezonlar açık, bugün kaç istek hakkı kaldı
  oranlar : iki lig için önümüzdeki maçların 1X2 oranlarını çeker ve data/api/oranlar.csv'ye EKLER
            (API eski oranları yalnızca ~7 gün tuttuğu için her gün çalıştırılır → kendi oran arşivimiz oluşur)

Anahtar koda YAZILMAZ; ortam değişkeninden okunur:
  GitHub'da: Settings → Secrets and variables → Actions → APIFOOTBALL_KEY
  Kendi bilgisayarında: export APIFOOTBALL_KEY="anahtar"   (Windows PowerShell: $env:APIFOOTBALL_KEY="anahtar")
Kullanım: python scripts/api_football_veri.py kontrol | oranlar
"""
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from ortak import LIGLER, VERI, guncel_sezon

TEMEL_URL = "https://v3.football.api-sports.io"


def istek(yol, **parametreler):
    anahtar = os.environ.get("APIFOOTBALL_KEY")
    url = f"{TEMEL_URL}/{yol}?{urllib.parse.urlencode(parametreler)}"
    req = urllib.request.Request(url, headers={"x-apisports-key": anahtar})
    with urllib.request.urlopen(req, timeout=30) as yanit:
        kalan = yanit.headers.get("x-ratelimit-requests-remaining")
        veri = json.load(yanit)
    if veri.get("errors"):
        raise RuntimeError(f"API hatası: {veri['errors']}")
    time.sleep(6.5)        # ücretsiz planın dakikalık sınırına takılmamak için
    return veri, kalan


def kontrol():
    for a in LIGLER.values():
        veri, kalan = istek("leagues", id=a["api_id"])
        lig = veri["response"][0]
        sezonlar = [s["year"] for s in lig["seasons"]]
        print(f"{a['ad']}: API'de '{lig['league']['name']}' ({lig['country']['name']}), sezonlar {sezonlar[0]}…{sezonlar[-1]}")
    print(f"Bugün kalan istek hakkı: {kalan}")


def oranlar():
    hedef = VERI / "api" / "oranlar.csv"; hedef.parent.mkdir(exist_ok=True)
    yeni = not hedef.exists()
    cekilme = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    satirlar = []; kalan = None
    for a in LIGLER.values():
        sayfa, toplam = 1, 1
        while sayfa <= toplam:
            veri, kalan = istek("odds", league=a["api_id"], season=guncel_sezon(), page=sayfa)
            toplam = veri["paging"]["total"]
            for kayit in veri["response"]:
                ev, ber, dep = [], [], []
                for sirket in kayit["bookmakers"]:
                    for bahis in sirket["bets"]:
                        if bahis["name"] != "Match Winner":
                            continue
                        d = {v["value"]: float(v["odd"]) for v in bahis["values"]}
                        if {"Home", "Draw", "Away"} <= d.keys():
                            ev.append(d["Home"]); ber.append(d["Draw"]); dep.append(d["Away"])
                if ev:
                    ort = lambda x: round(sum(x) / len(x), 3)
                    satirlar.append([cekilme, a["ad"], kayit["fixture"]["id"], kayit["fixture"]["date"][:10],
                                     len(ev), ort(ev), ort(ber), ort(dep)])
            sayfa += 1
    with open(hedef, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if yeni:
            w.writerow(["cekilme_zamani", "lig", "fixture_id", "mac_tarihi", "sirket_sayisi", "AvgH", "AvgD", "AvgA"])
        w.writerows(satirlar)
    print(f"{len(satirlar)} maçın oranı eklendi (kalan istek: {kalan})")


if __name__ == "__main__":
    if not os.environ.get("APIFOOTBALL_KEY"):
        print("APIFOOTBALL_KEY tanımlı değil; API adımı atlandı."); sys.exit(0)
    {"kontrol": kontrol, "oranlar": oranlar}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()
