"""
Geçmiş test (backtest): modeli geçmiş sezonlarda "geleceği görmeden" çalıştırır ve sonuçları
docs/veri/gecmis_test.json dosyasına yazar. Web sayfasındaki "Geçmiş test" bölümü buradan beslenir.

Her maç için model yalnızca o maçtan ÖNCE oynanmış maçlarla eğitilir (haftada bir yeniden eğitim).
Ağır bir hesap olduğu için günlük otomasyonda değil, model değiştiğinde elle çalıştırılır:
    python scripts/gecmis_test.py

Ölçütler:
  isabet          : en yüksek olasılık verilen sonucun gerçekleşme oranı
  Brier           : Σ (olasılık − gerçek[0/1])² ortalaması; düşük olan iyidir
  lig ortalaması  : her maça ligin genel ev / beraberlik / deplasman oranlarını vermek (takım bilgisi yok)
  açığın kapanan kısmı = (Brier_lig_ort − Brier_model) / (Brier_lig_ort − Brier_oranlar)
"""
import json
import warnings

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

from ortak import KOK, LIGLER, lig_dosyalari
import poisson_model as pm

warnings.filterwarnings("ignore")
BASLANGIC = {"super_lig": "2018-08-01", "premier_lig": "2015-08-01"}


def sezon(tarih):
    return np.where(tarih.dt.month >= 8, tarih.dt.year, tarih.dt.year - 1)


def kalibrasyon(P, y, kutular=(0, .1, .2, .3, .4, .5, .6, .7, .8, 1.0001)):
    p = P.ravel(); g = np.eye(3)[y].ravel(); sonuc = []
    for lo, hi in zip(kutular[:-1], kutular[1:]):
        m = (p >= lo) & (p < hi)
        if m.sum() >= 20:
            sonuc.append({"olasilik": round(float(p[m].mean()), 4), "gercek": round(float(g[m].mean()), 4), "n": int(m.sum())})
    return sonuc


def lig_testi(lig):
    df = pm.veri_oku(lig_dosyalari(lig))
    dc, alfa = pm.ayarlari_uygula(lig)
    P = pm.backtest(df, dc, alfa, pd.Timestamp(BASLANGIC[lig]))
    o = pm.oran_olasiliklari(df)
    y = df.sonuc.values
    s = sezon(df.Date)
    ok = ~np.isnan(P[:, 0]) & ~np.isnan(o).any(axis=1)
    # düzeltilmiş piyasa: favori–sürpriz yanlılığını düzelten üs, her sezon için yalnızca önceki sezonlardan öğrenilir
    D = np.full_like(o, np.nan)
    tum_oran = ~np.isnan(o).any(axis=1)
    for yil in sorted(set(s[ok])):
        tr = tum_oran & (s < yil); te = ok & (s == yil)
        b = minimize_scalar(lambda b: pm.log_kayip(pm.birlestir(o[tr], o[tr], 0, b), y[tr]),
                            bounds=(0.5, 2.0), method="bounded").x if tr.sum() > 500 else 1.0
        D[te] = pm.birlestir(o[te], o[te], 0, b)
    yy = y[ok]; Pm, Po, Pd = P[ok], o[ok], D[ok]
    sabit = np.tile(np.bincount(yy, minlength=3) / len(yy), (len(yy), 1))
    b_sabit, b_model, b_oran = pm.brier(sabit, yy), pm.brier(Pm, yy), pm.brier(Po, yy)
    emin = []
    for esik in (0.5, 0.6, 0.7):
        acc, n = pm.guclu_tahmin_isabeti(Pm, yy, esik)
        emin.append({"esik": esik, "n": n, "isabet": round(float(acc), 4)})
    sezonlar = []
    for yil in sorted(set(s[ok])):
        k = s[ok] == yil
        sezonlar.append({"sezon": f"{yil}-{(yil + 1) % 100:02d}", "n": int(k.sum()),
                         "brier_model": round(float(pm.brier(Pm[k], yy[k])), 4),
                         "brier_oran": round(float(pm.brier(Po[k], yy[k])), 4)})
    sonuc = {"ad": LIGLER[lig]["ad"], "donem": f"{df.Date[ok].min():%Y} – {df.Date[ok].max():%Y}", "n": int(ok.sum()),
             "isabet_model": round(float(pm.isabet(Pm, yy)), 4), "isabet_oran": round(float(pm.isabet(Po, yy)), 4),
             "isabet_ev": round(float(np.mean(yy == 0)), 4),
             "brier_lig_ortalamasi": round(float(b_sabit), 4), "brier_model": round(float(b_model), 4),
             "brier_oran": round(float(b_oran), 4), "brier_duzeltilmis": round(float(pm.brier(Pd, yy)), 4),
             "acik_kapanan": round(float((b_sabit - b_model) / (b_sabit - b_oran)), 4),
             "emin_tahminler": emin, "kalibrasyon": kalibrasyon(Pm, yy), "sezonlar": sezonlar}
    print(f"{sonuc['ad']}: {sonuc['n']} maç, isabet %{sonuc['isabet_model'] * 100:.1f}, Brier {b_model:.4f} "
          f"(lig ort. {b_sabit:.4f}, oranlar {b_oran:.4f}), açığın %{sonuc['acik_kapanan'] * 100:.0f}'ı kapandı")
    return sonuc


def main():
    veri = {"olusturma": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"),
            "ligler": {lig: lig_testi(lig) for lig in LIGLER}}
    hedef = KOK / "docs" / "veri" / "gecmis_test.json"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(json.dumps(veri, ensure_ascii=False), encoding="utf-8")
    print("Kaydedildi:", hedef.relative_to(KOK))


if __name__ == "__main__":
    main()
