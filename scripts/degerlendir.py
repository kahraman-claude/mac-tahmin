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

from ortak import LIGLER, RAPOR, TAHMIN, lig_dosyalari
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


def main():
    arsiv = TAHMIN / "arsiv.csv"
    if not arsiv.exists():
        print("Henüz arşivlenmiş tahmin yok."); return
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
    RAPOR.mkdir(exist_ok=True)
    (RAPOR / "performans.md").write_text("\n".join(satir) + "\n", encoding="utf-8")
    print(f"raporlar/performans.md yazıldı ({len(m)} değerlendirilmiş maç)")


if __name__ == "__main__":
    main()
