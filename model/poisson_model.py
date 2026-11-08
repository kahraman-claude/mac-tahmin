"""
Süper Lig maç tahmini — Adım 1: Poisson modeli + backtest
=========================================================

Bu script ne yapar?
1. football-data.co.uk formatındaki sezon CSV dosyalarını okur (T1.csv = Süper Lig).
2. Her takım için bir "atak gücü" ve bir "savunma gücü" öğrenir.
3. Geçmiş maçları "gelecekmiş gibi" tahmin eder (backtest): her tahmin anında
   model YALNIZCA o tarihten önceki maçları görür, yani hile yoktur.
4. Sonuçları üç kıyas noktasıyla karşılaştırır:
     - "Hep ev sahibi kazanır" kuralı
     - Bahis oranlarından hesaplanan olasılıklar (varsa)
     - Bizim Poisson modelimiz
5. Bir kalibrasyon grafiği çizer (calibration.png).

Kullanım:
    python3 poisson_model.py T1_2021.csv T1_2122.csv T1_2223.csv T1_2324.csv T1_2425.csv

------------------------------------------------------------------
MODELİN MATEMATİĞİ (her terimin anlamı)
------------------------------------------------------------------
Bir maçta ev sahibi takım i, deplasman takımı j olsun.

    λ_ev  = exp( μ + h + a_i − d_j )
    λ_dep = exp( μ       + a_j − d_i )

    λ_ev  (lambda ev)  : ev sahibinin bu maçta atması BEKLENEN gol sayısı
    λ_dep (lambda dep) : deplasmanın atması beklenen gol sayısı
    μ  (mü)            : ligin genel gol seviyesi (ortalama takımın ortalama gol beklentisi, log ölçeğinde)
    h                  : ev sahibi avantajı (log ölçeğinde; h = 0.25 → ev sahibi ~%28 fazla gol bekler)
    a_i                : takım i'nin atak gücü (pozitif = ortalamadan iyi hücum)
    d_j                : takım j'nin savunma gücü (pozitif = ortalamadan iyi savunma, rakibin golünü azaltır)
    exp(...)           : üstel fonksiyon; λ'nın her zaman pozitif olmasını sağlar

Gol sayısının Poisson dağıldığını varsayıyoruz:

    P(X = k) = λ^k · e^(−λ) / k!

    X  : atılan gol sayısı (rastgele değişken)
    k  : 0, 1, 2, 3, ... gibi belirli bir gol sayısı
    λ  : beklenen gol sayısı (yukarıda hesapladık)
    k! : k faktöriyel (k · (k−1) · ... · 1)

Skor matrisi: ev k gol, deplasman m gol atar olasılığı = P_ev(k) · P_dep(m)
(iki takımın gollerini bağımsız kabul ediyoruz — Dixon-Coles düzeltmesi sonraki adımda.)

    P(ev kazanır)  = matrisin köşegen ALTI   (k > m)
    P(beraberlik)  = matrisin köşegeni       (k = m)
    P(dep kazanır) = matrisin köşegen ÜSTÜ   (k < m)

Parametreleri bulmak (a, d, h, μ): "maksimum olabilirlik" yöntemi.
Geçmiş maçlarda gerçekleşen skorların olasılığını EN YÜKSEK yapan değerleri ararız.
Eski maçlar daha az önemli olsun diye zaman ağırlığı kullanırız:

    w = exp( −ξ · gün_farkı )

    w   : maçın ağırlığı (0 ile 1 arası)
    ξ   : (ksi) unutma hızı; büyükse model eski maçları daha çabuk "unutur"
    gün_farkı : maç ile tahmin günü arasındaki gün sayısı
"""

import sys
import re
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

MAX_GOL = 10          # skor matrisinde 0..10 gole kadar hesaplıyoruz
XI = np.log(2) / 120  # zaman ağırlığı: yarı ömür 120 gün (2018-22 doğrulamasında en iyi; 2023-26 testinde de iyileşti)
RIDGE = 0.05          # küçük ceza: veri azken atak/savunma değerlerini 0'a doğru çeker (aşırı uyumu engeller)
# Güç / tarz ayrımı (None ise ikisi de RIDGE/2 olur → eski davranışla birebir aynı):
#   güç  = a + d : takımın net kalitesi (iyi hücum + iyi savunma)
#   tarz = a − d : takımın maçlarının açıklığı (iyi hücum + zayıf savunma → gollü maçlar)
#   ceza = R_GUC · Σ(a+d)²  +  R_TARZ · Σ(a−d)²
R_GUC = None
R_TARZ = None
YENIDEN_EGIT_GUN = 7  # model her 7 günde bir yeniden eğitilir (yaklaşık her hafta)
ISINMA_GUN = 300      # ilk ~300 gün sadece eğitim verisi; tahmin yapmaya ondan sonra başlarız


# ------------------------------------------------------------------
# 1) VERİYİ OKUMA
# ------------------------------------------------------------------
# Aynı kulübün veri kaynağında farklı yazıldığı durumlar
AYNI_TAKIM = {"Middlesboro": "Middlesbrough"}


def veri_oku(dosyalar):
    parcalar = []
    for f in dosyalar:
        df = pd.read_csv(f, encoding="latin-1", on_bad_lines="skip")
        df.columns = [re.sub(r"^[^\x21-\x7e]+", "", str(c)).strip() for c in df.columns]
        df = df.dropna(subset=["HomeTeam", "AwayTeam", "FTHG", "FTAG"])
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
        df[["HomeTeam", "AwayTeam"]] = df[["HomeTeam", "AwayTeam"]].replace(AYNI_TAKIM)
        parcalar.append(df)
    df = pd.concat(parcalar, ignore_index=True)
    df = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    df["FTHG"] = df["FTHG"].astype(int)
    df["FTAG"] = df["FTAG"].astype(int)
    # Gerçek sonuç: 0 = ev kazandı, 1 = berabere, 2 = deplasman kazandı
    df["sonuc"] = np.select([df.FTHG > df.FTAG, df.FTHG == df.FTAG], [0, 1], 2)
    return df


def oran_olasiliklari(df):
    """Bahis oranlarını olasılığa çevirir.
    Oran O ise ham olasılık 1/O. Üç sonucun toplamı 1'den büyük çıkar
    (fark = bahis şirketinin kâr payı, 'marj'). Toplama bölerek marjı temizleriz."""
    # Sezona göre farklı sütunlar dolu: önce piyasa ortalaması (AvgH / BbAvH),
    # yoksa Pinnacle (PSH), o da yoksa Bet365 (B365H) — her maç için ilk dolu olan kullanılır.
    sonuc = np.full((len(df), 3), np.nan)
    for ev, ber, dep in [("AvgH", "AvgD", "AvgA"), ("BbAvH", "BbAvD", "BbAvA"),
                         ("PSH", "PSD", "PSA"), ("B365H", "B365D", "B365A")]:
        if all(c in df.columns for c in (ev, ber, dep)):
            ham = 1.0 / df[[ev, ber, dep]].apply(pd.to_numeric, errors="coerce").values
            olas = ham / ham.sum(axis=1, keepdims=True)
            bos = np.isnan(sonuc).any(axis=1)
            sonuc[bos] = olas[bos]
    return None if np.isnan(sonuc).all() else sonuc


# ------------------------------------------------------------------
# 2) MODELİ EĞİTME
# ------------------------------------------------------------------
def dc_tau(x, y, lam_ev, lam_dep, rho):
    """Dixon-Coles düzeltme çarpanı τ (tau).
    Sadece düşük skorlarda 1'den farklıdır:
        τ(0,0) = 1 − λ_ev·λ_dep·ρ     τ(0,1) = 1 + λ_ev·ρ
        τ(1,0) = 1 + λ_dep·ρ          τ(1,1) = 1 − ρ
        diğer bütün skorlarda τ = 1
    x, y   : ev ve deplasman golü
    λ_ev, λ_dep : beklenen goller
    ρ (rho): düzeltme gücü. ρ < 0 ise 0-0 ve 1-1 olasılığı ARTAR, 1-0 ve 0-1 AZALIR
             (futbolda düşük skorlu beraberlikler, bağımsız Poisson'un tahmininden sık görülür)."""
    tau = np.ones(np.broadcast(x, y, lam_ev).shape)
    tau = np.where((x == 0) & (y == 0), 1 - lam_ev * lam_dep * rho, tau)
    tau = np.where((x == 0) & (y == 1), 1 + lam_ev * rho, tau)
    tau = np.where((x == 1) & (y == 0), 1 + lam_dep * rho, tau)
    tau = np.where((x == 1) & (y == 1), 1 - rho, tau)
    return tau


def egit(gecmis, tahmin_gunu, dixon_coles=True, hedef=None):
    """hedef: None ise gerçek goller kullanılır. (ev_hedef, dep_hedef) dizileri verilirse
    takım güçleri bu "beklenen gol" değerlerine göre öğrenilir (ör. şut tabanlı xG).
    Dixon-Coles düzeltmesi her zaman GERÇEK skorlarla hesaplanır."""
    takimlar = sorted(set(gecmis.HomeTeam) | set(gecmis.AwayTeam))
    idx = {t: i for i, t in enumerate(takimlar)}
    n = len(takimlar)
    ev_i = gecmis.HomeTeam.map(idx).values
    dep_i = gecmis.AwayTeam.map(idx).values
    x = gecmis.FTHG.values            # ev golü
    y = gecmis.FTAG.values            # deplasman golü
    xt, yt = (x, y) if hedef is None else hedef   # takım gücünü öğrenmekte kullanılan hedef
    gun = (tahmin_gunu - gecmis.Date).dt.days.values
    w = np.exp(-XI * gun)
    m00, m01 = (x == 0) & (y == 0), (x == 0) & (y == 1)
    m10, m11 = (x == 1) & (y == 0), (x == 1) & (y == 1)

    # Parametre vektörü: [μ, h, ρ, a_1..a_n, d_1..d_n]
    def ayir(p):
        return p[0], p[1], p[2], p[3:3 + n], p[3 + n:]

    def nll_ve_gradyan(p):
        mu, h, rho, a, d = ayir(p)
        log_lam_ev = mu + h + a[ev_i] - d[dep_i]
        log_lam_dep = mu + a[dep_i] - d[ev_i]
        lam_ev, lam_dep = np.exp(log_lam_ev), np.exp(log_lam_dep)
        # Poisson log-olasılığı: k·ln(λ) − λ   (ln(k!) sabit olduğu için atıldı)
        ll = xt * log_lam_ev - lam_ev + yt * log_lam_dep - lam_dep
        r_ev = xt - lam_ev                 # ln(olasılık)'ın ln(λ_ev)'e göre türevi
        r_dep = yt - lam_dep
        g_rho = 0.0
        if dixon_coles:
            tau = np.clip(dc_tau(x, y, lam_ev, lam_dep, rho), 1e-10, None)
            ll = ll + np.log(tau)
            # ln(τ)'nun türevleri (yalnızca 4 düşük skorda sıfırdan farklı)
            r_ev = r_ev + np.where(m00, -lam_ev * lam_dep * rho / tau, 0) + np.where(m01, lam_ev * rho / tau, 0)
            r_dep = r_dep + np.where(m00, -lam_ev * lam_dep * rho / tau, 0) + np.where(m10, lam_dep * rho / tau, 0)
            d_rho = (np.where(m00, -lam_ev * lam_dep / tau, 0) + np.where(m01, lam_ev / tau, 0)
                     + np.where(m10, lam_dep / tau, 0) + np.where(m11, -1 / tau, 0))
            g_rho = -(w * d_rho).sum()
        r_ev, r_dep = w * r_ev, w * r_dep
        rg = RIDGE / 2 if R_GUC is None else R_GUC
        rt = RIDGE / 2 if R_TARZ is None else R_TARZ
        guc, tarz = a + d, a - d
        nll = -(w * ll).sum() + rg * (guc @ guc) + rt * (tarz @ tarz)
        g = np.zeros_like(p)
        g[0] = -(r_ev.sum() + r_dep.sum())
        g[1] = -r_ev.sum()
        g[2] = g_rho
        ga = np.bincount(ev_i, r_ev, n) + np.bincount(dep_i, r_dep, n)
        gd = -np.bincount(dep_i, r_ev, n) - np.bincount(ev_i, r_dep, n)
        g[3:3 + n] = -ga + 2 * rg * guc + 2 * rt * tarz
        g[3 + n:] = -gd + 2 * rg * guc - 2 * rt * tarz
        return nll, g

    p0 = np.zeros(3 + 2 * n)
    p0[0] = np.log(max(gecmis.FTAG.mean(), 0.1))
    p0[1] = 0.2
    sinirlar = [(None, None), (None, None), (-0.2, 0.2) if dixon_coles else (0, 0)] + [(None, None)] * (2 * n)
    sonuc = minimize(nll_ve_gradyan, p0, jac=True, method="L-BFGS-B", bounds=sinirlar)
    mu, h, rho, a, d = ayir(sonuc.x)
    return {"mu": mu, "h": h, "rho": rho,
            "a": dict(zip(takimlar, a)), "d": dict(zip(takimlar, d))}


# ------------------------------------------------------------------
# 3) TAHMİN: skor matrisi → 1X2 olasılıkları
# ------------------------------------------------------------------
def skor_matrisi(model, ev, dep, carpan_ev=1.0, carpan_dep=1.0):
    """carpan_ev / carpan_dep: beklenen gollere uygulanan ek düzeltme çarpanları
    (derbi, motivasyon gibi; bkz. duzeltme_carpanlari). 1.0 = düzeltme yok."""
    a = model["a"]; d = model["d"]
    lam_ev = np.exp(model["mu"] + model["h"] + a.get(ev, 0.0) - d.get(dep, 0.0)) * carpan_ev
    lam_dep = np.exp(model["mu"] + a.get(dep, 0.0) - d.get(ev, 0.0)) * carpan_dep
    k = np.arange(MAX_GOL + 1)
    matris = np.outer(poisson.pmf(k, lam_ev), poisson.pmf(k, lam_dep))
    rho = model.get("rho", 0.0)
    if rho:   # Dixon-Coles: sol üst 2x2 köşeyi (0-0, 0-1, 1-0, 1-1) τ ile düzelt
        xx, yy = np.meshgrid(k[:2], k[:2], indexing="ij")
        matris[:2, :2] *= dc_tau(xx, yy, lam_ev, lam_dep, rho)
    return matris / matris.sum(), lam_ev, lam_dep


def bir_x_iki(matris):
    p_ev = np.tril(matris, -1).sum()    # köşegen altı: ev golü > deplasman golü
    p_ber = np.trace(matris)            # köşegen: eşit gol
    p_dep = np.triu(matris, 1).sum()    # köşegen üstü
    return np.array([p_ev, p_ber, p_dep])


# ------------------------------------------------------------------
# 4) BACKTEST
# ------------------------------------------------------------------
def sut_katsayilari(gecmis):
    """Geçmiş maçlardan şutların gole dönüşme oranlarını öğrenir (en küçük kareler, sabitsiz):
        gol ≈ c_isabetli · isabetli_şut + c_diger · isabetsiz_şut
    c_isabetli : isabetli bir şutun ortalama gol değeri
    c_diger    : isabetsiz (kaleyi bulmayan) bir şutun ortalama gol değeri (genelde ~0)"""
    m = gecmis.HST.notna() & gecmis.HS.notna()
    if m.sum() < 200:
        return None
    g = gecmis[m]
    X = np.r_[np.c_[g.HST, g.HS - g.HST], np.c_[g.AST, g.AS - g.AST]].astype(float)
    hedef = np.r_[g.FTHG, g.FTAG].astype(float)
    c, *_ = np.linalg.lstsq(X, hedef, rcond=None)
    return np.clip(c, 0, None)


def sut_hedefi(gecmis, c, alfa):
    """Takım gücünü öğrenmek için karma hedef:
        hedef = alfa · gerçek_gol + (1 − alfa) · şut_xG
        şut_xG = c_isabetli · isabetli_şut + c_diger · isabetsiz_şut
    alfa = 1 → sadece gol, alfa = 0 → sadece şut. Şut verisi olmayan maçlarda gerçek gol kullanılır."""
    xg_ev = c[0] * gecmis.HST + c[1] * (gecmis.HS - gecmis.HST)
    xg_dep = c[0] * gecmis.AST + c[1] * (gecmis.AS - gecmis.AST)
    ev = (alfa * gecmis.FTHG + (1 - alfa) * xg_ev).fillna(gecmis.FTHG).values
    dep = (alfa * gecmis.FTAG + (1 - alfa) * xg_dep).fillna(gecmis.FTAG).values
    return ev, dep


def backtest(df, dixon_coles=True, alfa=1.0, baslangic=None):
    """alfa < 1 ise şut verisi kullanılır (sut_hedefi'ne bak)."""
    if baslangic is None:
        baslangic = df.Date.min() + pd.Timedelta(days=ISINMA_GUN)
    for kol in ("HS", "AS", "HST", "AST"):
        if kol not in df.columns:
            df[kol] = np.nan
    tahminler = np.full((len(df), 3), np.nan)
    model = None
    son_egitim = None
    for i, mac in df[df.Date >= baslangic].iterrows():
        if son_egitim is None or (mac.Date - son_egitim).days >= YENIDEN_EGIT_GUN:
            gecmis = df[(df.Date < mac.Date) & (df.Date >= mac.Date - pd.Timedelta(days=1500))]   # SADECE geçmiş maçlar (son ~4 yıl) → sızıntı yok
            model = egit(gecmis, mac.Date, dixon_coles)
            c = sut_katsayilari(gecmis) if alfa < 1 else None
            if c is not None:
                rho = model["rho"]   # ρ gerçek skorlardan öğrenildi; takım güçleri şut hedefinden
                model = egit(gecmis, mac.Date, False, hedef=sut_hedefi(gecmis, c, alfa))
                model["rho"] = rho
            son_egitim = mac.Date
        matris, _, _ = skor_matrisi(model, mac.HomeTeam, mac.AwayTeam)
        tahminler[i] = bir_x_iki(matris)
    return tahminler


# ------------------------------------------------------------------
# 5) ÖLÇÜMLER
# ------------------------------------------------------------------
def brier(olas, sonuc):
    """Brier skoru: her maç için Σ (tahmin olasılığı − gerçek[0/1])², sonra ortalama.
    0 = mükemmel. Her maça 1/3-1/3-1/3 demek ≈ 0.667 verir. Düşük olan iyidir."""
    gercek = np.eye(3)[sonuc]
    return np.mean(np.sum((olas - gercek) ** 2, axis=1))


def log_kayip(olas, sonuc):
    """Log kaybı: gerçekleşen sonuca verdiğin olasılığın −ln'inin ortalaması.
    Emin olup yanılmayı çok ağır cezalandırır. Düşük olan iyidir."""
    return -np.mean(np.log(np.clip(olas[np.arange(len(sonuc)), sonuc], 1e-12, 1)))


def isabet(olas, sonuc):
    """En yüksek olasılık verilen sonucun gerçekleşme oranı."""
    return np.mean(np.argmax(olas, axis=1) == sonuc)


def guclu_tahmin_isabeti(olas, sonuc, esik):
    maks = olas.max(axis=1)
    secili = maks >= esik
    if secili.sum() == 0:
        return np.nan, 0
    return isabet(olas[secili], sonuc[secili]), int(secili.sum())


def kalibrasyon_grafigi(olas, sonuc, dosya="calibration.png"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    p = olas.ravel()
    y = np.eye(3)[sonuc].ravel()
    kutular = np.linspace(0, 1, 11)
    ort_p, ort_y, adet = [], [], []
    for lo, hi in zip(kutular[:-1], kutular[1:]):
        m = (p >= lo) & (p < hi)
        if m.sum() >= 15:
            ort_p.append(p[m].mean()); ort_y.append(y[m].mean()); adet.append(m.sum())
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], "--", color="gray", label="Mükemmel kalibrasyon")
    ax.plot(ort_p, ort_y, "o-", color="#2563eb", label="Model")
    for x_, y_, n_ in zip(ort_p, ort_y, adet):
        ax.annotate(f"n={n_}", (x_, y_), textcoords="offset points", xytext=(6, -12), fontsize=8)
    ax.set_xlabel("Modelin verdiği olasılık")
    ax.set_ylabel("Gerçekleşme oranı")
    ax.set_title("Kalibrasyon: model '%X' dediğinde gerçekten %X mi oluyor?")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(dosya, dpi=130)
    return dosya


def rapor(df, tahminler):
    m = ~np.isnan(tahminler[:, 0])
    sonuc = df.sonuc.values[m]
    model_p = tahminler[m]
    satirlar = []

    ev_hep = np.tile([1.0, 0.0, 0.0], (len(sonuc), 1))
    satirlar.append(("Hep ev sahibi kazanır", isabet(ev_hep, sonuc), np.nan, np.nan))

    # Takım bilmeyen kıyas: her maça ligin genel oranlarını (ev/ber/dep yüzdeleri) vermek
    sabit = np.tile(np.bincount(sonuc, minlength=3) / len(sonuc), (len(sonuc), 1))
    satirlar.append(("Lig ortalaması (sabit)", isabet(sabit, sonuc),
                     brier(sabit, sonuc), log_kayip(sabit, sonuc)))

    oranlar = oran_olasiliklari(df)
    if oranlar is not None:
        o = oranlar[m]
        gecerli = ~np.isnan(o).any(axis=1)
        satirlar.append(("Bahis oranları", isabet(o[gecerli], sonuc[gecerli]),
                         brier(o[gecerli], sonuc[gecerli]), log_kayip(o[gecerli], sonuc[gecerli])))

    satirlar.append(("Poisson modelimiz", isabet(model_p, sonuc),
                     brier(model_p, sonuc), log_kayip(model_p, sonuc)))

    print(f"\nTest edilen maç sayısı: {len(sonuc)}  "
          f"({df.Date[m].min().date()} → {df.Date[m].max().date()})")
    print(f"Gerçek dağılım: ev %{np.mean(sonuc==0)*100:.1f} | "
          f"berabere %{np.mean(sonuc==1)*100:.1f} | deplasman %{np.mean(sonuc==2)*100:.1f}\n")
    print(f"{'Yöntem':<24}{'İsabet':>9}{'Brier':>9}{'LogKayıp':>10}")
    for ad, acc, b, l in satirlar:
        b_s = f"{b:.4f}" if not np.isnan(b) else "-"
        l_s = f"{l:.4f}" if not np.isnan(l) else "-"
        print(f"{ad:<24}{acc*100:>8.1f}%{b_s:>9}{l_s:>10}")

    print("\nModel emin olduğunda isabet:")
    for esik in (0.5, 0.6, 0.7):
        acc, n = guclu_tahmin_isabeti(model_p, sonuc, esik)
        if n:
            print(f"  olasılık ≥ %{int(esik*100)}: {n:4d} maç, isabet %{acc*100:.1f}")
    print("\nKalibrasyon grafiği:", kalibrasyon_grafigi(model_p, sonuc))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    df = veri_oku(sys.argv[1:])
    print(f"{len(df)} maç okundu, {df.HomeTeam.nunique()} farklı takım.")
    tahminler = backtest(df, dixon_coles=True, alfa=0.3)   # alfa=0.3: %30 gol + %70 şut tabanlı hedef
    rapor(df, tahminler)


# ------------------------------------------------------------------
# 6) MODEL + BAHİS ORANLARI BİRLEŞTİRME (logaritmik havuzlama)
# ------------------------------------------------------------------
def birlestir(p_model, p_oran, a, b):
    """İki olasılık tahminini birleştirir:
        p_birleşik(i) ∝ p_model(i)^a · p_oran(i)^b
    i          : sonuç (ev / beraberlik / deplasman)
    p_model(i) : bizim modelin olasılığı
    p_oran(i)  : bahis oranlarından gelen olasılık
    a, b       : iki kaynağa verilen ağırlıklar (a = 0 ise model hiç kullanılmaz)
    ∝          : "orantılıdır" — üç sonucun toplamı 1 olacak şekilde en sonda bölünür."""
    log_p = a * np.log(np.clip(p_model, 1e-9, 1)) + b * np.log(np.clip(p_oran, 1e-9, 1))
    p = np.exp(log_p - log_p.max(axis=1, keepdims=True))
    return p / p.sum(axis=1, keepdims=True)


def birlestirme_agirliklari(p_model, p_oran, sonuc):
    """a ve b'yi, geçmiş maçlardaki log kaybını en aza indirecek şekilde öğrenir."""
    def kayip(ab):
        return log_kayip(birlestir(p_model, p_oran, ab[0], ab[1]), sonuc)
    return minimize(kayip, [0.3, 1.0], method="Nelder-Mead").x


# ------------------------------------------------------------------
# 7) LİG BAZINDA AYARLAR (her lig kendi verisinde seçildi)
# ------------------------------------------------------------------
#   dixon_coles : Dixon-Coles düzeltmesi kullanılsın mı
#   alfa        : takım gücü hedefindeki golün payı (1 = sadece gol, 0.3 = %30 gol + %70 şut)
#   yari_omur   : zaman ağırlığının yarı ömrü (gün)
#   r_guc       : takımın net gücüne (a+d) uygulanan küçültme cezası
#   r_tarz      : takımın tarzına / maç açıklığına (a−d) uygulanan küçültme cezası
LIG_AYARLARI = {
    "super_lig":    {"dixon_coles": True, "alfa": 0.3, "yari_omur": 120, "r_guc": None, "r_tarz": None},
    "premier_lig":  {"dixon_coles": True, "alfa": 1.0, "yari_omur": 365, "r_guc": 1.0,  "r_tarz": 15.0},
    "la_liga":      {"dixon_coles": True, "alfa": 1.0, "yari_omur": 365, "r_guc": None, "r_tarz": None},   # geçici; geçmiş testle seçilecek
}


def ayarlari_uygula(lig):
    """Seçilen ligin ayarlarını modele uygular ve backtest için (dixon_coles, alfa) döndürür."""
    global XI, R_GUC, R_TARZ
    a = LIG_AYARLARI[lig]
    XI = np.log(2) / a["yari_omur"]
    R_GUC, R_TARZ = a["r_guc"], a["r_tarz"]
    return a["dixon_coles"], a["alfa"]


# ------------------------------------------------------------------
# 8) MAÇA ÖZGÜ DÜZELTMELER (ileriye dönük testte iyileşme sağlayanlar)
# ------------------------------------------------------------------
# Süper Lig büyük derbisi (Galatasaray, Fenerbahçe, Beşiktaş, Trabzonspor kendi aralarında):
#   iki takımın da beklenen golü × 0,885  (derbiler modelin beklediğinden ~%12 az gollü)
# Premier Lig, sezonun son 10 haftasında "hedefsiz" takım (ne üst sıralar ne küme hattı yarışında):
#   hedefsiz takımın kendi golü × 0,966, rakibinin golü × 1,093  (hedefsiz takım daha çok gol yiyor)
# Test edilip ETKİSİZ bulunanlar: dinlenme süresi, deplasman mesafesi, rakım, takıma özgü ev avantajı,
#   Premier Lig yerel derbileri, Süper Lig motivasyon etkisi.
BUYUK_DERBI_TR = {"Galatasaray", "Fenerbahce", "Besiktas", "Trabzonspor"}
DUZELTMELER = {
    "super_lig":   {"buyuk_derbi_gol": 0.885, "hedefsiz_kendi_gol": 1.0, "hedefsiz_rakip_gol": 1.0},
    "premier_lig": {"buyuk_derbi_gol": 1.0, "hedefsiz_kendi_gol": 0.966, "hedefsiz_rakip_gol": 1.093},
    "la_liga":     {"buyuk_derbi_gol": 1.0, "hedefsiz_kendi_gol": 1.0, "hedefsiz_rakip_gol": 1.0},
}


def duzeltme_carpanlari(lig, ev, dep, ev_hedefsiz=False, dep_hedefsiz=False):
    """(carpan_ev, carpan_dep) döndürür; skor_matrisi'ne verilir.
    ev_hedefsiz / dep_hedefsiz: takım sezonun son 10 haftasında hiçbir yarışın içinde değilse True
    (tanım için test_motivasyon.py'ye bak)."""
    k = DUZELTMELER[lig]; ce = cd = 1.0
    if ev in BUYUK_DERBI_TR and dep in BUYUK_DERBI_TR:
        ce *= k["buyuk_derbi_gol"]; cd *= k["buyuk_derbi_gol"]
    if ev_hedefsiz:
        ce *= k["hedefsiz_kendi_gol"]; cd *= k["hedefsiz_rakip_gol"]
    if dep_hedefsiz:
        cd *= k["hedefsiz_kendi_gol"]; ce *= k["hedefsiz_rakip_gol"]
    return ce, cd
