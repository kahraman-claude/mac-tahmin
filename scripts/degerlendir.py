"""
Canlı performans kaydı: arşivdeki tahminleri gerçekleşen sonuçlarla karşılaştırır.
Her maç için, maç gününden ÖNCE yapılmış en son tahmin kullanılır (sonradan düzeltme yok).
Çıktı: raporlar/performans.md

Ölçütler:
  isabet : en yüksek olasılık verilen sonucun gerçekleşme oranı
  Brier  : Σ (olasılık − gerçek[0/1])² ortalaması; düşük olan iyidir (her maça 1/3 demek ≈ 0,667)
Kullanım: python scripts/degerlendir.py
"""
import warnings

import numpy as np
import pandas as pd

import json

from ortak import KOK, LIGLER, RAPOR, TAHMIN, lig_dosyalari, takim_adi
import poisson_model as pm

warnings.filterwarnings("ignore")


def sonuclar():
    parca = []
    for lig, a in LIGLER.items():
        d = pm.veri_oku(lig_dosyalari(lig))
        parca.append(pd.DataFrame({"lig": a["ad"], "tarih": d.Date.dt.date.astype(str), "ev": d.HomeTeam,
                                   "deplasman": d.AwayTeam, "skor": d.FTHG.astype(str) + "-" + d.FTAG.astype(str),
                                   "sonuc": d.sonuc, "ust25": (d.FTHG + d.FTAG > 2).astype(int)}))
    return pd.concat(parca)


def olc(P, y):
    e = np.eye(3)[y]
    return np.mean(np.argmax(P, 1) == y), np.mean(((P - e) ** 2).sum(1))


def kalibrasyon(P, y, kutular=(0, .1, .2, .3, .4, .5, .6, .7, .8, 1.0001)):
    """Modelin verdiği olasılıkları aralıklara böler; her aralıkta ortalama olasılık ile gerçekleşme oranı."""
    p = P.ravel(); g = np.eye(3)[y].ravel(); sonuc = []
    for lo, hi in zip(kutular[:-1], kutular[1:]):
        m = (p >= lo) & (p < hi)
        if m.sum():
            sonuc.append({"olasilik": round(float(p[m].mean()), 4), "gercek": round(float(g[m].mean()), 4), "n": int(m.sum())})
    return sonuc


def site_yaz(m):
    ligler = {}
    for lig, a in LIGLER.items():
        g = m[m.lig == a["ad"]] if len(m) else m
        kayit = {"ad": a["ad"], "n": int(len(g))}
        if len(g):
            y = g.sonuc.values.astype(int); P = g[["model_1", "model_X", "model_2"]].values
            acc, br = olc(P, y)
            kayit.update({"isabet": round(float(acc), 4), "brier": round(float(br), 4),
                          "kalibrasyon": kalibrasyon(P, y)})
            o = g.dropna(subset=["piyasa_1"]) if "piyasa_1" in g else g.iloc[:0]
            if len(o):
                yo = o.sonuc.values.astype(int)
                kayit["piyasa"] = {"n": int(len(o)),
                                   "brier_model": round(float(olc(o[["model_1", "model_X", "model_2"]].values, yo)[1]), 4),
                                   "brier_piyasa": round(float(olc(o[["piyasa_1", "piyasa_X", "piyasa_2"]].values, yo)[1]), 4),
                                   "brier_duzeltilmis": round(float(olc(o[["duzeltilmis_1", "duzeltilmis_X", "duzeltilmis_2"]].values, yo)[1]), 4)}
            son = g.sort_values("tarih", ascending=False).head(40)
            kayit["son_maclar"] = [{"tarih": r.tarih, "ev": takim_adi(r.ev), "dep": takim_adi(r.deplasman), "skor": r.skor,
                                    "model": [r.model_1, r.model_X, r.model_2], "sonuc": int(r.sonuc)} for _, r in son.iterrows()]
        ligler[lig] = kayit
    hedef = KOK / "docs" / "veri" / "performans.json"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(json.dumps({"ligler": ligler}, ensure_ascii=False), encoding="utf-8")


def main():
    arsiv = TAHMIN / "arsiv.csv"
    if not arsiv.exists():
        print("Henüz arşivlenmiş tahmin yok."); site_yaz(pd.DataFrame()); return
    t = pd.read_csv(arsiv)
    t = t[t.calisma_zamani.str[:10] < t.tarih]                     # yalnızca maç gününden önce yapılmış tahminler
    t = t.sort_values("calisma_zamani").groupby(["lig", "tarih", "ev", "deplasman"]).tail(1)
    m = t.merge(sonuclar(), on=["lig", "tarih", "ev", "deplasman"], how="inner")
    satir = ["# Canlı performans kaydı\n",
             "Her maç için maç gününden önce yapılmış son tahmin kullanılır. "
             "Brier skorunda düşük olan iyidir; her maça 1/3 olasılık vermek ≈ 0,667 eder.\n"]
    if m.empty:
        satir.append("Henüz sonucu belli olmuş tahmin yok.")
    for lig, g in m.groupby("lig", sort=False):
        y = g.sonuc.values.astype(int)
        satir += [f"\n## {lig} — {len(g)} maç\n", "| Kaynak | İsabet | Brier |", "|---|---|---|"]
        acc, br = olc(g[["model_1", "model_X", "model_2"]].values, y)
        satir.append(f"| Model | %{acc * 100:.1f} | {br:.4f} |")
        o = g.dropna(subset=["piyasa_1"]) if "piyasa_1" in g else g.iloc[:0]
        if len(o):
            yo = o.sonuc.values.astype(int)
            for ad, k in (("Piyasa (bahis oranları)", "piyasa"), ("Düzeltilmiş piyasa", "duzeltilmis")):
                acc, br = olc(o[[f"{k}_1", f"{k}_X", f"{k}_2"]].values, yo)
                satir.append(f"| {ad} ({len(o)} maç) | %{acc * 100:.1f} | {br:.4f} |")
        b25 = np.mean((g["model_2.5ust"] - g.ust25) ** 2)
        satir.append(f"\n2,5 Üst/Alt Brier (model): {b25:.4f}\n")
        satir += ["| Tarih | Maç | Skor | Model 1 / X / 2 |", "|---|---|---|---|"]
        for _, r in g.sort_values("tarih", ascending=False).head(20).iterrows():
            satir.append(f"| {r.tarih} | {r.ev} – {r.deplasman} | {r.skor} | "
                         f"%{r.model_1 * 100:.0f} / %{r.model_X * 100:.0f} / %{r.model_2 * 100:.0f} |")
    site_yaz(m)
    RAPOR.mkdir(exist_ok=True)
    (RAPOR / "performans.md").write_text("\n".join(satir) + "\n", encoding="utf-8")
    print(f"raporlar/performans.md yazıldı ({len(m)} değerlendirilmiş maç)")


if __name__ == "__main__":
    main()
