"""
Önümüzdeki maçlar için tahmin üretir.
  1) Her lig için modeli bugüne kadarki bütün maçlarla eğitir (lig bazında seçilmiş ayarlarla).
  2) data/fixtures.csv içindeki önümüzdeki maçlar için olasılıkları hesaplar:
       - model olasılıkları (1X2, 2,5 Üst, karşılıklı gol, en olası skorlar)
       - piyasa olasılıkları (bahis oranlarından, marjı temizlenmiş)
       - düzeltilmiş piyasa olasılıkları (favori–sürpriz yanlılığı giderilmiş)
  3) Sonuçları kaydeder:
       tahminler/guncel.csv   : en son tahminler (her çalışmada yeniden yazılır)
       tahminler/arsiv.csv    : bütün tahminlerin geçmişi (canlı performans kaydı için)
       raporlar/bu_hafta.md   : GitHub'da okunabilir tablo
Kullanım: python scripts/tahmin.py
"""
import warnings
from datetime import datetime, timezone

import re

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

from ortak import LIGLER, RAPOR, TAHMIN, VERI, lig_dosyalari
import poisson_model as pm

warnings.filterwarnings("ignore")


def modeli_egit(df, lig, gun):
    dc, alfa = pm.ayarlari_uygula(lig)
    for k in ("HS", "AS", "HST", "AST"):
        if k not in df:
            df[k] = np.nan
    g = df[(df.Date < gun) & (df.Date >= gun - pd.Timedelta(days=1500))]
    model = pm.egit(g, gun, dc)
    c = pm.sut_katsayilari(g) if alfa < 1 else None
    if c is not None:                       # takım güçleri şut + gol karma hedefinden, ρ gerçek skorlardan
        rho = model["rho"]
        model = pm.egit(g, gun, False, hedef=pm.sut_hedefi(g, c, alfa))
        model["rho"] = rho
    return model


def piyasa_us_degeri(df):
    """Bahis oranlarındaki favori–sürpriz yanlılığını düzelten üs b'yi geçmiş maçlardan öğrenir:
        p_düzeltilmiş(i) ∝ p_oran(i)^b      (b > 1 → favoriler güçlenir, sürprizler zayıflar)"""
    o = pm.oran_olasiliklari(df)
    if o is None:
        return 1.0
    m = ~np.isnan(o).any(axis=1) & (df.Date >= df.Date.max() - pd.Timedelta(days=365 * 8)).values
    if m.sum() < 500:
        return 1.0
    y = df.sonuc.values[m]
    return minimize_scalar(lambda b: pm.log_kayip(pm.birlestir(o[m], o[m], 0, b), y),
                           bounds=(0.5, 2.0), method="bounded").x


def hedefsiz_durumu(df, gun, takimlar_maclar, son_hafta=10, esik=1.5):
    """Sezonun son 10 haftasında takımın hiçbir yarışın içinde olup olmadığını bulur
    (tanım ve test için ana klasördeki test_motivasyon.py'ye bakın)."""
    sezon_bas = pd.Timestamp(year=gun.year if gun.month >= 8 else gun.year - 1, month=7, day=1)
    s = df[(df.Date >= sezon_bas) & (df.Date < gun)]
    takimlar = sorted(set(s.HomeTeam) | set(s.AwayTeam))
    N = len(takimlar)
    if N < 10:
        return {}
    P = {t: 0 for t in takimlar}; AV = {t: 0 for t in takimlar}; OM = {t: 0 for t in takimlar}
    for _, m in s.iterrows():
        for t, a, y in ((m.HomeTeam, m.FTHG, m.FTAG), (m.AwayTeam, m.FTAG, m.FTHG)):
            P[t] += 3 if a > y else 1 if a == y else 0; AV[t] += a - y; OM[t] += 1
    sira = sorted(takimlar, key=lambda t: (P[t], AV[t]), reverse=True)
    ust_cizgi, alt_cizgi = P[sira[3]], P[sira[N - 3]]
    durum = {}
    for t in takimlar_maclar:
        if t not in P:
            continue
        kalan = 2 * (N - 1) - OM[t]
        if kalan > son_hafta:
            durum[t] = False; continue
        ust = sira.index(t) <= 3 or (ust_cizgi - P[t]) <= esik * kalan
        alt = (P[t] - alt_cizgi) <= esik * kalan
        durum[t] = not (ust or alt)
    return durum


def lig_tahmini(lig, fikstur, gun):
    a = LIGLER[lig]
    df = pm.veri_oku(lig_dosyalari(lig))
    son_yil = df[(df.Date < gun) & (df.Date >= gun - pd.Timedelta(days=365))]
    if len(son_yil) < 100:
        print(f"UYARI: {a['ad']} için son bir yılda yalnızca {len(son_yil)} maç var; veri güncel değil, lig atlandı.")
        return pd.DataFrame()
    model = modeli_egit(df, lig, gun)
    b = piyasa_us_degeri(df)
    f = fikstur[(fikstur.Div == a["kod"]) & (fikstur.Date >= gun)].copy()
    if f.empty:
        print(f"{a['ad']}: önümüzdeki maç bulunamadı (fixtures.csv'de henüz yok)")
        return pd.DataFrame()
    hedefsiz = hedefsiz_durumu(df, gun, set(f.HomeTeam) | set(f.AwayTeam))
    bilinen = set(model["a"])
    satirlar = []
    for _, m in f.iterrows():
        uyari = ", ".join(t for t in (m.HomeTeam, m.AwayTeam) if t not in bilinen)
        ce, cd = pm.duzeltme_carpanlari(lig, m.HomeTeam, m.AwayTeam,
                                        hedefsiz.get(m.HomeTeam, False), hedefsiz.get(m.AwayTeam, False))
        M, le, ld = pm.skor_matrisi(model, m.HomeTeam, m.AwayTeam, ce, cd)
        p = pm.bir_x_iki(M)
        k = np.arange(M.shape[0])
        ust25 = M[(k[:, None] + k[None, :]) > 2].sum()
        kg = 1 - M[0, :].sum() - M[:, 0].sum() + M[0, 0]
        en_olasi = sorted(((M[i, j], i, j) for i in range(6) for j in range(6)), reverse=True)[:3]
        satir = {"lig": a["ad"], "tarih": m.Date.date().isoformat(), "saat": m.get("Time", ""),
                 "ev": m.HomeTeam, "deplasman": m.AwayTeam,
                 "beklenen_gol_ev": round(le, 2), "beklenen_gol_dep": round(ld, 2),
                 "model_1": round(p[0], 4), "model_X": round(p[1], 4), "model_2": round(p[2], 4),
                 "model_2.5ust": round(ust25, 4), "model_kg_var": round(kg, 4),
                 "en_olasi_skorlar": " | ".join(f"{i}-{j} %{q * 100:.0f}" for q, i, j in en_olasi),
                 "uyari": f"modelde verisi olmayan takım: {uyari}" if uyari else ""}
        oran = [m.get(c) for c in ("AvgH", "AvgD", "AvgA")]
        if all(pd.notna(x) and float(x) > 1 for x in oran):
            ham = 1 / np.array(oran, dtype=float); po = ham / ham.sum()
            pdz = pm.birlestir(po[None, :], po[None, :], 0, b)[0]
            satir.update({"piyasa_1": round(po[0], 4), "piyasa_X": round(po[1], 4), "piyasa_2": round(po[2], 4),
                          "duzeltilmis_1": round(pdz[0], 4), "duzeltilmis_X": round(pdz[1], 4),
                          "duzeltilmis_2": round(pdz[2], 4)})
        satirlar.append(satir)
    print(f"{a['ad']}: {len(satirlar)} maç tahmin edildi (piyasa üssü b = {b:.2f})")
    return pd.DataFrame(satirlar)


def rapor_yaz(t, calisma):
    t = t.fillna({"uyari": "", "saat": ""})
    yuzde = lambda x: "" if pd.isna(x) else f"%{x * 100:.0f}"
    satir = [f"# Tahminler\n\nSon güncelleme: {calisma} (UTC)\n",
             "Model olasılıkları; parantez içinde varsa düzeltilmiş piyasa olasılığı. "
             "İstatistiksel tahmindir, bahis tavsiyesi değildir.\n"]
    for lig, g in t.groupby("lig", sort=False):
        satir += [f"\n## {lig}\n", "| Tarih | Maç | 1 | X | 2 | 2,5 Üst | KG Var | En olası skor |",
                  "|---|---|---|---|---|---|---|---|"]
        for _, r in g.iterrows():
            ek = lambda c: f" ({yuzde(r.get('duzeltilmis_' + c))})" if pd.notna(r.get("duzeltilmis_" + c)) else ""
            satir.append(f"| {r.tarih} {r.saat} | {r.ev} – {r.deplasman} | {yuzde(r.model_1)}{ek('1')} | "
                         f"{yuzde(r.model_X)}{ek('X')} | {yuzde(r.model_2)}{ek('2')} | {yuzde(r['model_2.5ust'])} | "
                         f"{yuzde(r.model_kg_var)} | {r.en_olasi_skorlar.split(' | ')[0]} |")
        uy = g[g.uyari != ""]
        for _, r in uy.iterrows():
            satir.append(f"\n> Uyarı ({r.ev} – {r.deplasman}): {r.uyari}")
    (RAPOR / "bu_hafta.md").write_text("\n".join(satir) + "\n", encoding="utf-8")


def main():
    gun = pd.Timestamp.today().normalize()
    calisma = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    fikstur = pd.read_csv(VERI / "fixtures.csv", encoding="latin-1", on_bad_lines="skip")
    # dosyanın başındaki görünmez BOM karakterini sütun adlarından temizle ("ï»¿Div" → "Div")
    fikstur.columns = [re.sub(r"^[^\x21-\x7e]+", "", str(c)).strip() for c in fikstur.columns]
    fikstur["Date"] = pd.to_datetime(fikstur["Date"], dayfirst=True, errors="coerce")
    tum = [lig_tahmini(lig, fikstur, gun) for lig in LIGLER]
    t = pd.concat([x for x in tum if not x.empty], ignore_index=True) if any(not x.empty for x in tum) else pd.DataFrame()
    if t.empty:
        print("Tahmin edilecek maç yok."); return
    t.insert(0, "calisma_zamani", calisma)
    TAHMIN.mkdir(exist_ok=True); RAPOR.mkdir(exist_ok=True)
    t.to_csv(TAHMIN / "guncel.csv", index=False)
    arsiv = TAHMIN / "arsiv.csv"
    if arsiv.exists():
        t = pd.concat([pd.read_csv(arsiv), t], ignore_index=True)
    t["_gun"] = t.calisma_zamani.str[:10]
    t = t.drop_duplicates(["_gun", "lig", "tarih", "ev", "deplasman"], keep="last").drop(columns="_gun")
    t.to_csv(arsiv, index=False)
    rapor_yaz(pd.read_csv(TAHMIN / "guncel.csv"), calisma)
    print("Kaydedildi: tahminler/guncel.csv, tahminler/arsiv.csv, raporlar/bu_hafta.md")


if __name__ == "__main__":
    main()
