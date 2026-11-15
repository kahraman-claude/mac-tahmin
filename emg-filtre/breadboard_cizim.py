"""
Breadboard yerleşim çizimi üretir ve bağlantıları otomatik doğrular.

Çalıştır:  python breadboard_cizim.py   ->  breadboard.html

Yerleşim, her parçanın bacaklarının hangi deliğe takıldığı olarak tanımlanır.
Breadboard'un iç bağlantıları (a-e ve f-j sütun şeritleri, güç hatları) ile
birleştirilip elde edilen devre, README'deki devre şemasıyla (BEKLENEN) karşılaştırılır.
En küçük farkta betik hata verir; yani çizim elektriksel olarak doğrulanmıştır.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

SUTUN = 63
UST = "abcde"
ALT = "fghij"
RAYLAR = {"P+": "+9 V", "PG": "GND", "QG": "GND", "Q-": "−9 V"}

# --------------------------------------------------------------------------
# Yerleşim
# Delik adları: 'a10', 'j44' ...  Güç hatları: 'P+5' (üst +9 V), 'PG5' (üst GND),
#                                 'QG5' (alt GND), 'Q-5' (alt −9 V)
# Her parça: (kimlik, tür, değer, kat, [(bacak adı, delik), ...], açıklama)
# --------------------------------------------------------------------------
P = []


def parca(kimlik, tur, deger, kat, bacaklar, aciklama="", yol=None):
    P.append(dict(id=kimlik, tur=tur, deger=deger, kat=kat, bacaklar=bacaklar, aciklama=aciklama, yol=yol))


# --- Entegreler (ikisi de çentik SOLDA) ---
parca("U1", "ic", "AD620", "ina",
      [("1", "f8"), ("2", "f9"), ("3", "f10"), ("4", "f11"),
       ("5", "e11"), ("6", "e10"), ("7", "e9"), ("8", "e8")],
      "Enstrümantasyon yükselteci. Çentik solda, 1. bacak sol altta.")
parca("U2", "ic", "LM324", "lm",
      [("1", "f40"), ("2", "f41"), ("3", "f42"), ("4", "f43"), ("5", "f44"), ("6", "f45"), ("7", "f46"),
       ("8", "e46"), ("9", "e45"), ("10", "e44"), ("11", "e43"), ("12", "e42"), ("13", "e41"), ("14", "e40")],
      "Dörtlü op-amp. Çentik solda, 1. bacak sol altta. A,B: çentik filtre; C: alçak geçiren; D: kazanç.")

# --- Güç ---
parca("BAT1", "pil", "9 V", "guc", [("+", "P+1"), ("-", "PG1")], "Üst pil: + ucu +9 V hattına, − ucu GND hattına")
parca("BAT2", "pil", "9 V", "guc", [("+", "QG1"), ("-", "Q-1")], "Alt pil: + ucu GND hattına, − ucu −9 V hattına")
parca("C_B1", "elko", "10 µF", "guc", [("+", "P+3"), ("-", "PG3")], "Elektrolitik: uzun bacak (+) +9 V hattına")
parca("C_B2", "elko", "10 µF", "guc", [("+", "QG3"), ("-", "Q-3")], "Elektrolitik: uzun bacak (+) GND hattına, kısa bacak −9 V'a")
parca("C_D1", "seramik", "100 nF", "guc", [("1", "P+6"), ("2", "PG6")], "AD620 dekuplaj (+9 V)")
parca("C_D2", "seramik", "100 nF", "guc", [("1", "QG6"), ("2", "Q-6")], "AD620 dekuplaj (−9 V)")
parca("C_D3", "seramik", "100 nF", "guc", [("1", "P+50"), ("2", "PG50")], "LM324 dekuplaj (+9 V)")
parca("C_D4", "seramik", "100 nF", "guc", [("1", "QG50"), ("2", "Q-50")], "LM324 dekuplaj (−9 V)")
parca("W_GND", "kopru", "", "guc", [("1", "PG60"), ("2", "QG60")], "Üst ve alt GND hatlarını birleştirir")
parca("W_U1V+", "tel", "", "guc", [("1", "a9"), ("2", "P+9")], "AD620 bacak 7 → +9 V")
parca("W_U1V-", "tel", "", "guc", [("1", "j11"), ("2", "Q-11")], "AD620 bacak 4 → −9 V")
parca("W_U1REF", "kopru", "", "guc", [("1", "d11"), ("2", "PG13")], "AD620 bacak 5 (REF) → GND")
parca("W_U2V+", "kopru", "", "guc", [("1", "i43"), ("2", "P+37")], "LM324 bacak 4 → +9 V (entegrenin solundan dolaşarak üst hatta)", yol=[37.6, 37.2])
parca("W_U2V-", "kopru", "", "guc", [("1", "b43"), ("2", "Q-55")], "LM324 bacak 11 → −9 V (entegrenin sağından dolaşarak alt hatta)", yol=[55.4, 55.4])
parca("W_VR", "kopru", "", "guc", [("1", "a48"), ("2", "Q-57")], "48. sütunun üst yarısını −9 V yapar (C çıkış direnci için)", yol=[57.4, 57.4])

# --- [1] AD620 ve elektrotlar ---
parca("E_N", "elektrot", "Elektrot −", "ina", [("1", "j2")], "Biseps üzerindeki 2. elektrot")
parca("E_P", "elektrot", "Elektrot +", "ina", [("1", "j4")], "Biseps üzerindeki 1. elektrot")
parca("E_R", "elektrot", "Referans", "ina", [("1", "g5")], "Dirsekteki referans elektrodu")
parca("R_EN", "direnc", "10k", "ina", [("1", "i2"), ("2", "i9")], "Koruma direnci: elektrot − → AD620 bacak 2")
parca("R_EP", "direnc", "10k", "ina", [("1", "h4"), ("2", "h10")], "Koruma direnci: elektrot + → AD620 bacak 3")
parca("R_ER", "direnc", "10k", "ina", [("1", "j5"), ("2", "QG5")], "Koruma direnci: referans elektrot → GND")
parca("W_RG1", "tel", "", "ina", [("1", "b8"), ("2", "b7")], "AD620 bacak 8 → RG")
parca("R_G", "direnc", "1k", "ina", [("1", "d7"), ("2", "f7")], "RG: kazancı 50,4 yapar (kanalın üzerinden geçer)")
parca("W_RG2", "tel", "", "ina", [("1", "g7"), ("2", "g8")], "RG → AD620 bacak 1")
parca("TP1", "prob", "CH1", "ina", [("1", "b10")], "Osiloskop CH1: ham sinyal (AD620 çıkışı)")

# --- [2] Twin-T çentik (üst yarı, 10-26. sütunlar) + LM324 A, B ---
parca("R_T1", "direnc", "30k", "centik", [("1", "a10"), ("2", "a15")], "Twin-T üst kol, R'nin 1. parçası")
parca("R_T2", "direnc", "1,8k", "centik", [("1", "b15"), ("2", "b18")], "Twin-T üst kol, R'nin 2. parçası (30k+1,8k = 31,8k)")
parca("R_T3", "direnc", "30k", "centik", [("1", "a18"), ("2", "a23")], "Twin-T üst kol, ikinci R'nin 1. parçası")
parca("R_T4", "direnc", "1,8k", "centik", [("1", "b23"), ("2", "b26")], "Twin-T üst kol, ikinci R'nin 2. parçası")
parca("C_T1", "film", "100n", "centik", [("1", "c10"), ("2", "c12")], "Twin-T alt kol C")
parca("C_T2", "film", "100n", "centik", [("1", "d12"), ("2", "d14")], "Twin-T alt kol C")
parca("W_T1", "kopru", "", "centik", [("1", "e14"), ("2", "c26")], "Alt kolun sonu → üst kolun sonu (çentik çıkışı)")
parca("C_T3", "film", "100n", "centik", [("1", "c18"), ("2", "c20")], "2C'nin yarısı (üst kol ortası → Vf)")
parca("C_T4", "film", "100n", "centik", [("1", "d18"), ("2", "d20")], "2C'nin diğer yarısı (paralel)")
parca("R_T5", "direnc", "13k", "centik", [("1", "e12"), ("2", "f12")], "R/2'nin sabit kısmı (kanalın üzerinden geçer)")
parca("TRIM", "trimpot", "5k", "centik", [("1", "g12"), ("2", "g13"), ("3", "g14")],
      "R/2'nin ayarlı kısmı. Orta bacak (wiper) Vf'ye gider. 50 Hz'de çıkış en küçük olana kadar çevirin.")
parca("W_T2", "kopru", "", "centik", [("1", "d26"), ("2", "g42")], "Çentik çıkışı → LM324 bacak 3 (+IN A)")
parca("W_T3", "kopru", "", "centik", [("1", "e20"), ("2", "h46")], "2C → Vf (LM324 bacak 7)")
parca("W_T4", "kopru", "", "centik", [("1", "h13"), ("2", "b20")], "Trimpot orta bacak → Vf (2C ile aynı nokta)")
parca("W_A", "tel", "", "centik", [("1", "g40"), ("2", "g41")], "LM324 A izleyici: bacak 2 ↔ bacak 1")
parca("W_B", "tel", "", "centik", [("1", "g45"), ("2", "g46")], "LM324 B izleyici: bacak 6 ↔ bacak 7")
parca("R_A", "direnc", "1k", "centik", [("1", "h40"), ("2", "h44")], "Ra: geri besleme bölücüsü (çıkış → +IN B)")
parca("R_B", "direnc", "9,1k", "centik", [("1", "j44"), ("2", "QG44")], "Rb: geri besleme bölücüsü (+IN B → GND)")
parca("R_PA", "direnc", "10k", "lm", [("1", "j40"), ("2", "Q-40")], "LM324 çıkış direnci (A) → −9 V")
parca("R_PB", "direnc", "10k", "lm", [("1", "j46"), ("2", "Q-46")], "LM324 çıkış direnci (B) → −9 V")
parca("W_TP2", "kopru", "", "ag", [("1", "i40"), ("2", "c53")], "Çentik çıkışı (TP2) → alçak geçiren girişi")

# --- [3] Sallen-Key alçak geçiren (üst sağ) + LM324 C ---
parca("R_S1", "direnc", "33k", "ag", [("1", "d53"), ("2", "d49")], "Sallen-Key R1")
parca("R_S2", "direnc", "33k", "ag", [("1", "b49"), ("2", "b44")], "Sallen-Key R2 → LM324 bacak 10 (+IN C)")
parca("C_S1", "film", "10n", "ag", [("1", "c49"), ("2", "c47")], "Sallen-Key C1 (geri besleme, çıkışa)")
parca("C_S2", "film", "10n", "ag", [("1", "a44"), ("2", "PG44")], "Sallen-Key C2 → GND")
parca("R_SG", "direnc", "10k", "ag", [("1", "a45"), ("2", "PG45")], "Sallen-Key Rg → GND")
parca("R_SF", "direnc", "5,6k", "ag", [("1", "c45"), ("2", "c46")], "Sallen-Key Rf (dik takılır)")
parca("W_C", "tel", "", "ag", [("1", "a46"), ("2", "a47")], "LM324 bacak 8 (TP3) → 47. sütun")
parca("R_PC", "direnc", "10k", "lm", [("1", "d47"), ("2", "d48")], "LM324 çıkış direnci (C) → −9 V (dik takılır)")

# --- [4] Yüksek geçiren + kazanç (üst sol) + LM324 D ---
parca("C_H", "film", "1µ", "kazanc", [("1", "d46"), ("2", "d42")], "Yüksek geçiren C (kutupsuz film)")
parca("R_H", "direnc", "8,2k", "kazanc", [("1", "a42"), ("2", "PG42")], "Yüksek geçiren R → GND")
parca("R_KG", "direnc", "10k", "kazanc", [("1", "a41"), ("2", "PG41")], "Kazanç Rg → GND")
parca("R_KF", "direnc", "120k", "kazanc", [("1", "b41"), ("2", "b40")], "Kazanç Rf (dik takılır)")
parca("R_PD", "direnc", "10k", "lm", [("1", "c40"), ("2", "c43")], "LM324 çıkış direnci (D) → bacak 11 (−9 V)")
parca("TP4", "prob", "CH2", "kazanc", [("1", "d40")], "Osiloskop CH2: filtrelenmiş çıkış")
parca("GNDP", "prob", "GND", "guc", [("1", "PG30")], "Osiloskop prob toprak klipsleri")

# --------------------------------------------------------------------------
# Beklenen devre (README'deki şema). Uç adları: 'parça.bacak'
# --------------------------------------------------------------------------
BEKLENEN = {
    "+9 V": ["BAT1.+", "C_B1.+", "C_D1.1", "C_D3.1", "U1.7", "U2.4"],
    "GND": ["BAT1.-", "BAT2.+", "C_B1.-", "C_B2.+", "C_D1.2", "C_D2.1", "C_D3.2", "C_D4.1", "U1.5",
            "R_ER.2", "R_B.2", "C_S2.2", "R_SG.2", "R_H.2", "R_KG.2", "GNDP.1"],
    "−9 V": ["BAT2.-", "C_B2.-", "C_D2.2", "C_D4.2", "U1.4", "U2.11", "R_PA.2", "R_PB.2", "R_PC.2", "R_PD.2"],
    "Elektrot −": ["E_N.1", "R_EN.1"],
    "Elektrot +": ["E_P.1", "R_EP.1"],
    "Referans elektrot": ["E_R.1", "R_ER.1"],
    "AD620 −IN": ["R_EN.2", "U1.2"],
    "AD620 +IN": ["R_EP.2", "U1.3"],
    "RG (bacak 8)": ["U1.8", "R_G.1"],
    "RG (bacak 1)": ["U1.1", "R_G.2"],
    "TP1 (ham sinyal)": ["U1.6", "R_T1.1", "C_T1.1", "TP1.1"],
    "Twin-T R ara 1": ["R_T1.2", "R_T2.1"],
    "Twin-T üst kol ortası": ["R_T2.2", "R_T3.1", "C_T3.1", "C_T4.1"],
    "Twin-T R ara 2": ["R_T3.2", "R_T4.1"],
    "Twin-T çıkışı": ["R_T4.2", "C_T2.2", "U2.3"],
    "Twin-T alt kol ortası": ["C_T1.2", "C_T2.1", "R_T5.1"],
    "R/2 ara": ["R_T5.2", "TRIM.1"],
    "Vf (geri besleme)": ["TRIM.2", "C_T3.2", "C_T4.2", "U2.7", "U2.6", "R_PB.1"],
    "Trimpot boş bacak": ["TRIM.3"],
    "TP2 (çentik çıkışı)": ["U2.1", "U2.2", "R_A.1", "R_PA.1", "R_S1.1"],
    "+IN B": ["U2.5", "R_A.2", "R_B.1"],
    "Sallen-Key orta": ["R_S1.2", "R_S2.1", "C_S1.1"],
    "+IN C": ["R_S2.2", "U2.10", "C_S2.1"],
    "−IN C": ["U2.9", "R_SG.1", "R_SF.1"],
    "TP3 (alçak geçiren çıkışı)": ["U2.8", "R_SF.2", "C_S1.2", "C_H.1", "R_PC.1"],
    "+IN D": ["C_H.2", "U2.12", "R_H.1"],
    "−IN D": ["U2.13", "R_KG.1", "R_KF.1"],
    "TP4 (çıkış)": ["U2.14", "R_KF.2", "R_PD.1", "TP4.1"],
}

TEL_TURLERI = {"tel", "kopru"}


def dugum(delik: str) -> str:
    for r in RAYLAR:
        if delik.startswith(r):
            return r
    satir, sutun = delik[0], int(delik[1:])
    assert 1 <= sutun <= SUTUN, delik
    return f"U{sutun}" if satir in UST else f"A{sutun}"


def dogrula():
    # 1) Her delikte en fazla bir bacak
    dolu = {}
    for p in P:
        for b, d in p["bacaklar"]:
            assert d not in dolu, f"{d} deliği iki kez kullanılmış: {dolu[d]} ve {p['id']}.{b}"
            dolu[d] = f"{p['id']}.{b}"

    # 2) Aynı satırda yatay uzanan parçalar üst üste binmesin (çizim okunurluğu)
    yatay = defaultdict(list)
    for p in P:
        if p["tur"] in {"kopru", "ic"} or len(p["bacaklar"]) < 2:
            continue
        d1, d2 = p["bacaklar"][0][1], p["bacaklar"][-1][1]
        if any(d1.startswith(r) or d2.startswith(r) for r in RAYLAR):
            continue
        if d1[0] == d2[0]:
            a, b = sorted([int(d1[1:]), int(d2[1:])])
            for (c, e, kim) in yatay[d1[0]]:
                assert b < c or a > e, f"{p['id']} ile {kim} {d1[0]} satırında üst üste biniyor"
            yatay[d1[0]].append((a, b, p["id"]))

    # 3) Elektriksel karşılaştırma
    ebeveyn = {}

    def bul(x):
        ebeveyn.setdefault(x, x)
        while ebeveyn[x] != x:
            ebeveyn[x] = ebeveyn[ebeveyn[x]]
            x = ebeveyn[x]
        return x

    def birlestir(a, b):
        ebeveyn[bul(a)] = bul(b)

    birlestir("PG", "PG")
    for p in P:
        if p["tur"] in TEL_TURLERI:
            birlestir(dugum(p["bacaklar"][0][1]), dugum(p["bacaklar"][1][1]))
    uc_dugum = {}
    for p in P:
        if p["tur"] in TEL_TURLERI:
            continue
        for b, d in p["bacaklar"]:
            uc_dugum[f"{p['id']}.{b}"] = bul(dugum(d))

    tum_uclar = set(uc_dugum)
    beklenen_uclar = {u for v in BEKLENEN.values() for u in v}
    assert tum_uclar == beklenen_uclar, (
        f"Eksik: {sorted(beklenen_uclar - tum_uclar)}  Fazla: {sorted(tum_uclar - beklenen_uclar)}")

    ag_kok = {}
    for ad, uclar in BEKLENEN.items():
        kokler = {uc_dugum[u] for u in uclar}
        assert len(kokler) == 1, f"'{ad}' bağlantısı kopuk: " + ", ".join(
            f"{u}@{uc_dugum[u]}" for u in uclar)
        kok = kokler.pop()
        assert kok not in ag_kok, f"'{ad}' ile '{ag_kok[kok]}' kısa devre!"
        ag_kok[kok] = ad

    # Her deliğin ait olduğu bağlantı adı (etkileşimli vurgulama için)
    delik_ag = {}
    for satir in UST + ALT:
        for s in range(1, SUTUN + 1):
            k = bul(dugum(f"{satir}{s}"))
            if k in ag_kok:
                delik_ag[f"{satir}{s}"] = ag_kok[k]
    for r in RAYLAR:
        k = bul(r)
        for s in range(1, SUTUN + 1):
            delik_ag[f"{r}{s}"] = ag_kok.get(k, RAYLAR[r])
    print(f"Doğrulandı: {len(P)} parça, {len(BEKLENEN)} bağlantı, kısa devre veya kopukluk yok.")
    return delik_ag


# --------------------------------------------------------------------------
# Çizim (SVG)
# --------------------------------------------------------------------------
A = 16          # delik aralığı (px)
X0 = 46         # 1. sütunun x'i
Y = {}
y = 34
for r in ["P+", "PG"]:
    Y[r] = y
    y += A
y += A
for r in UST:
    Y[r] = y
    y += A
y += A  # orta kanal
for r in ALT:
    Y[r] = y
    y += A
y += A
for r in ["QG", "Q-"]:
    Y[r] = y
    y += A
YUKSEKLIK = y + 30
TUVAL_Y = YUKSEKLIK + 66
GENISLIK = X0 + (SUTUN - 1) * A + 46
KANAL_Y = (Y["e"] + Y["f"]) / 2


def xy(delik):
    for r in RAYLAR:
        if delik.startswith(r):
            return X0 + (int(delik[len(r):]) - 1) * A, Y[r]
    return X0 + (int(delik[1:]) - 1) * A, Y[delik[0]]


def svg_cizim(delik_ag):
    o = []
    w = o.append
    w(f'<svg id="bb" viewBox="0 0 {GENISLIK} {TUVAL_Y}" xmlns="http://www.w3.org/2000/svg" '
      f'role="img" aria-label="Breadboard yerleşimi">')
    # Kart
    w(f'<rect x="8" y="10" width="{GENISLIK-16}" height="{YUKSEKLIK-20}" rx="10" class="kart"/>')
    w(f'<rect x="20" y="{KANAL_Y-5}" width="{GENISLIK-40}" height="10" rx="3" class="kanal"/>')
    # Güç hattı çizgileri
    for r, sinif in [("P+", "ray-art"), ("PG", "ray-eks"), ("QG", "ray-eks"), ("Q-", "ray-art")]:
        yy = Y[r] + (-9 if r in ("P+",) else 9 if r in ("Q-",) else (9 if r == "PG" else -9))
        w(f'<line x1="30" x2="{GENISLIK-30}" y1="{yy}" y2="{yy}" class="{sinif}"/>')
        etiket = RAYLAR[r]
        w(f'<text x="{GENISLIK-26}" y="{Y[r]+4}" class="ray-yazi">{etiket}</text>')
    # Satır ve sütun etiketleri
    for r in UST + ALT:
        w(f'<text x="{X0-22}" y="{Y[r]+4}" class="koord">{r}</text>')
    for s in range(1, SUTUN + 1):
        if s == 1 or s % 5 == 0:
            x = X0 + (s - 1) * A
            w(f'<text x="{x}" y="{Y["a"]-10}" class="koord" text-anchor="middle">{s}</text>')
            w(f'<text x="{x}" y="{Y["Q-"]+20}" class="koord" text-anchor="middle">{s}</text>')
    # Delikler
    for r in list(RAYLAR) + list(UST + ALT):
        for s in range(1, SUTUN + 1):
            d = f"{r}{s}"
            x, yy = xy(d)
            ag = delik_ag.get(d, "")
            w(f'<rect x="{x-3.5}" y="{yy-3.5}" width="7" height="7" rx="1.5" class="delik" '
              f'data-ag="{ag}" data-d="{d}"/>')

    # Parçalar: önce gövdeler, en son köprü teller (üstte görünsünler)
    sira = sorted(P, key=lambda p: {"ic": 0, "kopru": 9, "prob": 10, "elektrot": 10}.get(p["tur"], 5))
    for p in sira:
        w(parca_svg(p, delik_ag))
    w('</svg>')
    return "\n".join(o)


def bacak_aglari(p, delik_ag):
    return "|".join(sorted({delik_ag.get(d, "") for _, d in p["bacaklar"]} - {""}))


def parca_svg(p, delik_ag):
    t, kim, kat = p["tur"], p["id"], p["kat"]
    ortak = f'class="parca kat-{kat} tur-{t}" data-id="{kim}" data-ag="{bacak_aglari(p, delik_ag)}" tabindex="0"'
    nok = [xy(d) for _, d in p["bacaklar"]]
    s = []
    if t == "ic":
        xs = [x for x, _ in nok]
        x1, x2 = min(xs) - 7, max(xs) + 7
        y1, y2 = Y["e"] - 2, Y["f"] + 2
        s.append(f'<g {ortak}>')
        s.append(f'<rect x="{x1}" y="{y1}" width="{x2-x1}" height="{y2-y1}" rx="3" class="ic-govde"/>')
        s.append(f'<path d="M{x1} {KANAL_Y-5} a5 5 0 0 1 0 10" class="ic-centik"/>')
        s.append(f'<text x="{(x1+x2)/2}" y="{KANAL_Y+4}" class="ic-yazi" text-anchor="middle">{p["deger"]}</text>')
        for b, d in p["bacaklar"]:
            x, yy = xy(d)
            s.append(f'<rect x="{x-3}" y="{yy-3}" width="6" height="6" class="ic-bacak"/>')
            ty = yy - 7 if d[0] in UST else yy + 13
            s.append(f'<text x="{x}" y="{ty}" class="ic-no" text-anchor="middle">{b}</text>')
        s.append('</g>')
        return "".join(s)

    if t in ("elektrot", "prob"):
        (x, yy), = nok
        if t == "elektrot":
            ex, ey = 18, yy + (40 if p["bacaklar"][0][1][0] == "j" else 72)
            ey = min(ey, YUKSEKLIK - 6)
            ey = YUKSEKLIK + 18 + {"E_N": 0, "E_P": 18, "E_R": 36}[kim]
            ex = 70 + {"E_N": 0, "E_P": 0, "E_R": 0}[kim]
            s.append(f'<g {ortak}><path d="M{x} {yy} C{x} {ey} {x+10} {ey} {ex+40} {ey}" class="kablo elektrot-kablo"/>'
                     f'<circle cx="{x}" cy="{yy}" r="3.5" class="uc"/>'
                     f'<rect x="{ex+40}" y="{ey-8}" width="104" height="16" rx="8" class="elektrot-etiket"/>'
                     f'<text x="{ex+92}" y="{ey+4}" class="elektrot-yazi" text-anchor="middle">{p["deger"]}</text></g>')
            return "".join(s)
        # prob: bayrak
        if kim == "TP4":  # sola doğru bayrak (LM324 çevresi kalabalık)
            bx = x - 52
            s.append(f'<g {ortak}><line x1="{x}" y1="{yy}" x2="{bx+34}" y2="{yy}" class="prob-cubuk"/>'
                     f'<rect x="{bx}" y="{yy-7}" width="34" height="14" rx="3" class="prob-bayrak"/>'
                     f'<text x="{bx+17}" y="{yy+3}" class="prob-yazi" text-anchor="middle">{p["deger"]}</text>'
                     f'<circle cx="{x}" cy="{yy}" r="3.5" class="uc"/></g>')
            return "".join(s)
        yon = -1 if not p["bacaklar"][0][1].startswith("Q") else 1
        by = yy - 26 if yon < 0 else yy + 26
        s.append(f'<g {ortak}><line x1="{x}" y1="{yy}" x2="{x}" y2="{by}" class="prob-cubuk"/>'
                 f'<rect x="{x-17}" y="{by-15}" width="34" height="14" rx="3" class="prob-bayrak"/>'
                 f'<text x="{x}" y="{by-5}" class="prob-yazi" text-anchor="middle">{p["deger"]}</text>'
                 f'<circle cx="{x}" cy="{yy}" r="3.5" class="uc"/></g>')
        return "".join(s)

    if t == "pil":
        (x1, y1), (x2, y2) = nok
        bx = 14
        s.append(f'<g {ortak}><path d="M{x1} {y1} H{bx}" class="kablo pil-art"/>'
                 f'<path d="M{x2} {y2} H{bx}" class="kablo pil-eks"/>'
                 f'<rect x="2" y="{min(y1,y2)-6}" width="12" height="{abs(y2-y1)+12}" rx="2" class="pil-govde"/>'
                 f'<circle cx="{x1}" cy="{y1}" r="3" class="uc"/><circle cx="{x2}" cy="{y2}" r="3" class="uc"/></g>')
        return "".join(s)

    if t == "trimpot":
        xs = [x for x, _ in nok]
        yy = nok[0][1]
        s.append(f'<g {ortak}><rect x="{min(xs)-6}" y="{yy+2}" width="{max(xs)-min(xs)+12}" height="14" rx="2" class="trim-govde"/>'
                 + "".join(f'<line x1="{x}" y1="{yy}" x2="{x}" y2="{yy+3}" class="bacak"/>' for x in xs)
                 + f'<circle cx="{max(xs)+1}" cy="{yy+9}" r="3" class="trim-vida"/>'
                 f'<text x="{min(xs)+6}" y="{yy+13}" class="govde-yazi" text-anchor="middle">5k</text></g>')
        return "".join(s)

    (x1, y1), (x2, y2) = nok[0], nok[-1]
    if t == "kopru":
        dx, dy = x2 - x1, y2 - y1
        L = max((dx * dx + dy * dy) ** 0.5, 1)
        if p.get("yol"):
            cx1 = X0 + (p["yol"][0] - 1) * A
            cx2 = X0 + (p["yol"][1] - 1) * A
            c1, c2 = (cx1, y1 + (y2 - y1) * 0.05), (cx2, y2 - (y2 - y1) * 0.05)
        else:
            h = min(30, 8 + 0.07 * L)
            nx, ny = -dy / L, dx / L
            if ny > 0:
                nx, ny = -nx, -ny
            c1 = (x1 + dx * 0.25 + nx * h, y1 + dy * 0.25 + ny * h)
            c2 = (x2 - dx * 0.25 + nx * h, y2 - dy * 0.25 + ny * h)
        renk = "tel-guc" if kat == "guc" else "tel-sinyal"
        if kim in ("W_U2V-", "W_VR"):
            renk = "tel-eksi"
        if kim in ("W_U2V+",):
            renk = "tel-arti"
        if kim in ("W_GND", "W_U1REF"):
            renk = "tel-gnd"
        return (f'<g {ortak}><path d="M{x1} {y1} C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {x2} {y2}" class="kablo {renk}"/>'
                f'<circle cx="{x1}" cy="{y1}" r="3" class="uc"/><circle cx="{x2}" cy="{y2}" r="3" class="uc"/></g>')
    if t == "tel":
        renk = {"W_U1V+": "tel-arti", "W_U1V-": "tel-eksi"}.get(kim, "tel-sinyal")
        return (f'<g {ortak}><line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="kablo duz {renk}"/>'
                f'<circle cx="{x1}" cy="{y1}" r="3" class="uc"/><circle cx="{x2}" cy="{y2}" r="3" class="uc"/></g>')

    # İki bacaklı gövdeli parçalar
    dx, dy = x2 - x1, y2 - y1
    L = max((dx * dx + dy * dy) ** 0.5, 1)
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    s.append(f'<g {ortak}>')
    if L < 1.5 * A:  # dik takılan parça: gövdeyi yukarı kaldır
        cy = my - 14
        s.append(f'<path d="M{x1} {y1} Q{x1} {cy} {mx} {cy} Q{x2} {cy} {x2} {y2}" class="bacak"/>')
        mx, my = mx, cy
        dx, dy, L = 1, 0, 1
    else:
        s.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="bacak"/>')
    aci = __import__("math").degrees(__import__("math").atan2(dy, dx))
    if aci > 90 or aci < -90:
        aci += 180
    if t == "direnc":
        g, h, sinif = 24, 9, "direnc-govde"
    elif t == "film":
        g, h, sinif = 16, 10, "film-govde"
    elif t == "seramik":
        g, h, sinif = 9, 9, "seramik-govde"
    elif t == "elko":
        g, h, sinif = 11, 11, "elko-govde"
    else:
        g, h, sinif = 16, 9, "direnc-govde"
    rx = h / 2 if t in ("seramik", "elko") else 3
    s.append(f'<g transform="translate({mx:.1f} {my:.1f}) rotate({aci:.1f})">'
             f'<rect x="{-g/2}" y="{-h/2}" width="{g}" height="{h}" rx="{rx}" class="{sinif}"/>')
    if t in ("direnc", "film"):
        s.append(f'<text x="0" y="3" class="govde-yazi" text-anchor="middle">{p["deger"]}</text>')
    s.append('</g>')
    s.append(f'<circle cx="{x1}" cy="{y1}" r="2.6" class="uc"/><circle cx="{x2}" cy="{y2}" r="2.6" class="uc"/></g>')
    return "".join(s)


# --------------------------------------------------------------------------
# HTML
# --------------------------------------------------------------------------
KATLAR = [
    ("guc", "Güç", "Piller, güç hatları, dekuplaj kondansatörleri"),
    ("ina", "[1] AD620", "Elektrotlar, koruma dirençleri, RG"),
    ("centik", "[2] Çentik filtre", "Twin-T, trimpot, LM324 A ve B"),
    ("ag", "[3] Alçak geçiren", "Sallen-Key, LM324 C"),
    ("kazanc", "[4] Yüksek geçiren + kazanç", "LM324 D"),
    ("lm", "LM324 çıkış dirençleri", "Her çıkıştan −9 V'a 10k"),
]


def html(svg, delik_ag):
    parcalar = {p["id"]: dict(deger=p["deger"], tur=p["tur"], kat=p["kat"], aciklama=p["aciklama"],
                              delikler=[f"{b}: {d}" if len(p["bacaklar"]) > 1 else d for b, d in p["bacaklar"]])
                for p in P}
    katlar_html = "".join(
        f'<button type="button" class="kat-btn" id="k-{k}" data-kat="{k}" aria-pressed="false">'
        f'<span class="nokta kat-{k}"></span><span><b>{ad}</b><small>{alt}</small></span></button>'
        for k, ad, alt in KATLAR)
    return f"""<title>EMG Breadboard Yerleşimi</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;500;600&family=Space+Grotesk:wght@500;700&display=swap">
<style>
/* Düzen: üstte başlık ve kat seçici, ortada yatay kaydırılabilir breadboard, altta seçili parça/bağlantı paneli */
:root {{
  --bg: #eef1f4; --yuzey: #ffffff; --fg: #1b2430; --soluk: #5d6b7a; --cizgi: #d3dae2;
  --kart: #f7f8fa; --kart-kenar: #cfd6de; --delik: #b9c2cc; --kanal: #dfe4ea;
  --arti: #d33a2c; --eksi: #2c5fd3; --gnd: #1b2430;
  --vurgu: #0f8b8d; --vurgu-zemin: rgba(15,139,141,.14);
  --ic: #23272e; --ic-yazi: #eef1f4;
  --direnc: #e3c79a; --film: #d8a630; --seramik: #e08a3c; --elko: #2d4f8f; --trim: #2f6fd6;
  --k-guc: #7b8794; --k-ina: #8a5cd6; --k-centik: #d6455c; --k-ag: #2b9a5f; --k-kazanc: #d98a1c; --k-lm: #4b8fd6;
  --tel: #2b9a5f;
  --f-baslik: "Space Grotesk", "Segoe UI", system-ui, sans-serif;
  --f-metin: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
  --f-kod: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #12161b; --yuzey: #1a2028; --fg: #e6ebf0; --soluk: #95a3b2; --cizgi: #2c3542;
  --kart: #232a33; --kart-kenar: #36414e; --delik: #10141a; --kanal: #1b2129;
  --arti: #ff6b5c; --eksi: #6e9bff; --gnd: #c9d2dc;
  --vurgu: #3cc7c3; --vurgu-zemin: rgba(60,199,195,.16);
  --ic: #0b0d10; --ic-yazi: #dfe5ea;
  --direnc: #cdb187; --film: #c99a2b; --seramik: #d47d33; --elko: #4c74c2; --trim: #4d86e8;
  --tel: #45c07e; color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --bg: #12161b; --yuzey: #1a2028; --fg: #e6ebf0; --soluk: #95a3b2; --cizgi: #2c3542;
  --kart: #232a33; --kart-kenar: #36414e; --delik: #10141a; --kanal: #1b2129;
  --arti: #ff6b5c; --eksi: #6e9bff; --gnd: #c9d2dc;
  --vurgu: #3cc7c3; --vurgu-zemin: rgba(60,199,195,.16);
  --ic: #0b0d10; --ic-yazi: #dfe5ea;
  --direnc: #cdb187; --film: #c99a2b; --seramik: #d47d33; --elko: #4c74c2; --trim: #4d86e8;
  --tel: #45c07e; color-scheme: dark; }}
* {{ box-sizing: border-box; }}
body {{ background: var(--bg); color: var(--fg); font-family: var(--f-metin); font-size: 15px; line-height: 1.5;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  padding-block: 20px 40px; }}
.sar {{ max-width: 1180px; margin: 0 auto; display: grid; gap: 18px; }}
h1 {{ font-family: var(--f-baslik); font-size: clamp(22px, 3vw, 30px); margin: 0; text-wrap: balance; letter-spacing: -.01em; }}
.ust p {{ margin: 6px 0 0; color: var(--soluk); max-width: 70ch; }}
.uyari {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.cip {{ font-size: 13px; padding: 4px 10px; border-radius: 999px; background: var(--yuzey); border: 1px solid var(--cizgi); }}
.cip b {{ font-family: var(--f-kod); font-weight: 600; }}
.katlar {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 8px; }}
.kat-btn {{ display: flex; gap: 10px; align-items: flex-start; text-align: left; padding: 9px 11px; border-radius: 8px;
  background: var(--yuzey); border: 1px solid var(--cizgi); color: var(--fg); font: inherit; cursor: pointer; }}
.kat-btn small {{ display: block; color: var(--soluk); font-size: 12px; line-height: 1.35; }}
.kat-btn b {{ font-weight: 600; font-size: 14px; }}
.kat-btn[aria-pressed="true"] {{ border-color: var(--vurgu); background: var(--vurgu-zemin); }}
.kat-btn:focus-visible, .parca:focus-visible {{ outline: 2px solid var(--vurgu); outline-offset: 2px; }}
.nokta {{ width: 12px; height: 12px; border-radius: 50%; margin-top: 4px; flex: none; }}
.nokta.kat-guc {{ background: var(--k-guc); }} .nokta.kat-ina {{ background: var(--k-ina); }}
.nokta.kat-centik {{ background: var(--k-centik); }} .nokta.kat-ag {{ background: var(--k-ag); }}
.nokta.kat-kazanc {{ background: var(--k-kazanc); }} .nokta.kat-lm {{ background: var(--k-lm); }}
.tahta {{ background: var(--yuzey); border: 1px solid var(--cizgi); border-radius: 12px; padding: 10px; overflow-x: auto; }}
#bb {{ display: block; width: 100%; min-width: 980px; height: auto; font-family: var(--f-kod); }}
.kart {{ fill: var(--kart); stroke: var(--kart-kenar); }}
.kanal {{ fill: var(--kanal); }}
.ray-art {{ stroke: var(--arti); stroke-width: 1.5; }} .ray-eks {{ stroke: var(--eksi); stroke-width: 1.5; }}
.ray-yazi {{ font-size: 9px; fill: var(--soluk); }}
.koord {{ font-size: 8.5px; fill: var(--soluk); }}
.delik {{ fill: var(--delik); }}
.delik.yan {{ fill: var(--vurgu); }}
.ic-govde {{ fill: var(--ic); }} .ic-centik {{ fill: var(--kart); }}
.ic-yazi {{ font-size: 11px; font-weight: 600; fill: var(--ic-yazi); letter-spacing: .04em; }}
.ic-bacak {{ fill: #9aa4ae; }} .ic-no {{ font-size: 8px; fill: var(--fg); font-weight: 600; }}
.bacak {{ stroke: #8d969f; stroke-width: 1.6; fill: none; }}
.uc {{ fill: #8d969f; }}
.direnc-govde {{ fill: var(--direnc); stroke: rgba(0,0,0,.25); }}
.film-govde {{ fill: var(--film); stroke: rgba(0,0,0,.25); }}
.seramik-govde {{ fill: var(--seramik); }} .elko-govde {{ fill: var(--elko); }}
.trim-govde {{ fill: var(--trim); }} .trim-vida {{ fill: #e9c46a; }}
.govde-yazi {{ font-size: 7.5px; fill: #1b2430; font-weight: 600; }}
.kablo {{ fill: none; stroke-width: 3; stroke-linecap: round; opacity: .92; }}
.tel-sinyal {{ stroke: var(--tel); }} .tel-arti {{ stroke: var(--arti); }} .tel-eksi {{ stroke: var(--eksi); }}
.tel-gnd, .tel-guc {{ stroke: var(--gnd); }}
.pil-art {{ stroke: var(--arti); }} .pil-eks {{ stroke: var(--gnd); }}
.pil-govde {{ fill: var(--soluk); }}
.elektrot-kablo {{ stroke: var(--k-ina); stroke-dasharray: 5 3; }}
.elektrot-etiket {{ fill: var(--k-ina); }} .elektrot-yazi {{ font-size: 10px; fill: #fff; font-weight: 600; }}
.prob-cubuk {{ stroke: var(--soluk); stroke-width: 1.5; }}
.prob-bayrak {{ fill: var(--fg); }} .prob-yazi {{ font-size: 9px; fill: var(--bg); font-weight: 600; }}
.parca {{ cursor: pointer; transition: opacity .15s; }}
#bb.odak .parca {{ opacity: .18; }}
#bb.odak .parca.secik {{ opacity: 1; }}
#bb.odak .parca.secik .kablo {{ stroke-width: 4; }}
.alt {{ display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); gap: 16px; }}
@media (max-width: 760px) {{ .alt {{ grid-template-columns: 1fr; }} }}
.panel {{ background: var(--yuzey); border: 1px solid var(--cizgi); border-radius: 12px; padding: 14px 16px; min-width: 0; }}
.panel h2 {{ font-family: var(--f-baslik); font-size: 17px; margin: 0 0 8px; }}
.panel p {{ margin: 0 0 8px; }}
.etiket {{ font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--soluk); font-weight: 600; }}
.delik-listesi {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 4px 0 10px; padding: 0; list-style: none; }}
.delik-listesi li {{ font-family: var(--f-kod); font-size: 13px; padding: 2px 8px; border-radius: 6px; background: var(--vurgu-zemin); }}
ol.adim {{ margin: 0; padding-left: 20px; display: grid; gap: 6px; }}
ol.adim li::marker {{ font-family: var(--f-kod); color: var(--soluk); }}
code {{ font-family: var(--f-kod); font-size: .92em; }}
@media (prefers-reduced-motion: reduce) {{ .parca {{ transition: none; }} }}
</style>

<div class="sar">
  <header class="ust">
    <h1>EMG filtre devresi — breadboard yerleşimi</h1>
    <p>AD620 + LM324 devresinin 830 delikli breadboard üzerindeki yerleşimi. Bir parçaya veya deliğe dokunun:
    o noktaya elektriksel olarak bağlı her şey vurgulanır. Bu yerleşim bir betikle README'deki devre şemasına karşı
    tek tek doğrulandı.</p>
  </header>
  <div class="uyari">
    <span class="cip">İki entegrenin de çentiği <b>solda</b>, 1. bacak sol altta</span>
    <span class="cip">Üst hatlar: <b>+9 V</b> ve <b>GND</b> · Alt hatlar: <b>GND</b> ve <b>−9 V</b></span>
    <span class="cip">Güç hatları ortadan kesikse kısa bir tel ile birleştirin</span>
  </div>
  <div class="katlar" role="group" aria-label="Katları göster">{katlar_html}</div>
  <div class="tahta">{svg}</div>
  <div class="alt">
    <section class="panel" id="bilgi" aria-live="polite">
      <h2 id="b-baslik">Bir parça seçin</h2>
      <p id="b-metin" style="color:var(--soluk)">Breadboard üzerindeki bir parçaya veya deliğe dokunun. Yukarıdaki
      kat düğmeleriyle devrenin bir bölümünü tek başına gösterebilirsiniz.</p>
      <div id="b-detay" hidden>
        <div class="etiket">Takıldığı delikler</div>
        <ul class="delik-listesi" id="b-delik"></ul>
        <div class="etiket">Bağlı olduğu noktalar</div>
        <ul class="delik-listesi" id="b-ag"></ul>
      </div>
    </section>
    <section class="panel">
      <h2>Kurulum sırası</h2>
      <ol class="adim">
        <li>Pilleri <b>bağlamadan</b> önce güç tellerini ve köprüleri takın; GND hatlarını 60. sütundaki tel ile birleştirin.</li>
        <li>AD620'yi 8–11. sütunlara, LM324'ü 40–46. sütunlara kanalın üzerine oturtun.</li>
        <li><b>Güç</b> katını takın, pilleri bağlayın; AD620 bacak 7'de +9 V, bacak 4'te −9 V ölçün. Sonra pilleri çıkarın.</li>
        <li>Katları sırayla ekleyin: <b>[2] çentik</b> → <b>[3] alçak geçiren</b> → <b>[4] kazanç</b>. Her katı README'deki jeneratör testiyle deneyin.</li>
        <li>Trimpotu 50 Hz sinüs verip LM324 bacak 1'de çıkış en küçük olana kadar çevirin.</li>
        <li>En son <b>[1]</b> katının elektrotlarını bağlayın. CH1'i <code>b10</code>'a, CH2'yi <code>c40</code>'a, prob topraklarını üst GND hattına takın.</li>
      </ol>
    </section>
  </div>
</div>
<script>
const PARCA = {json.dumps(parcalar, ensure_ascii=False)};
const svg = document.getElementById('bb');
const baslik = document.getElementById('b-baslik'), metin = document.getElementById('b-metin');
const detay = document.getElementById('b-detay'), dl = document.getElementById('b-delik'), al = document.getElementById('b-ag');
const TUR = {{direnc:'Direnç', film:'Film kondansatör', seramik:'Seramik kondansatör', elko:'Elektrolitik kondansatör',
  trimpot:'Çok turlu trimpot', ic:'Entegre', tel:'Tel', kopru:'Köprü tel', pil:'Pil', prob:'Osiloskop probu', elektrot:'Elektrot kablosu'}};
function temizle() {{
  svg.classList.remove('odak');
  svg.querySelectorAll('.secik').forEach(e => e.classList.remove('secik'));
  svg.querySelectorAll('.delik.yan').forEach(e => e.classList.remove('yan'));
}}
function liste(el, ogeler) {{ el.replaceChildren(...ogeler.map(t => {{ const li = document.createElement('li'); li.textContent = t; return li; }})); }}
function aglariVurgula(aglar) {{
  svg.querySelectorAll('.delik').forEach(d => {{ if (aglar.includes(d.dataset.ag)) d.classList.add('yan'); }});
}}
function parcaSec(g) {{
  temizle(); document.querySelectorAll('.kat-btn').forEach(b => b.setAttribute('aria-pressed', 'false'));
  const p = PARCA[g.dataset.id]; const aglar = g.dataset.ag ? g.dataset.ag.split('|') : [];
  svg.classList.add('odak'); g.classList.add('secik'); aglariVurgula(aglar);
  baslik.textContent = (p.deger ? p.deger + ' · ' : '') + (TUR[p.tur] || p.tur);
  metin.textContent = p.aciklama || ''; metin.style.color = '';
  liste(dl, p.delikler); liste(al, aglar); detay.hidden = false;
}}
function agSec(ad, delik) {{
  temizle(); document.querySelectorAll('.kat-btn').forEach(b => b.setAttribute('aria-pressed', 'false'));
  if (!ad) return;
  svg.classList.add('odak'); aglariVurgula([ad]);
  svg.querySelectorAll('.parca').forEach(g => {{ if ((g.dataset.ag || '').split('|').includes(ad)) g.classList.add('secik'); }});
  baslik.textContent = ad; metin.textContent = delik + ' deliği bu noktaya bağlı. Vurgulanan parçalar da bu noktaya bağlı.';
  metin.style.color = ''; detay.hidden = true;
}}
svg.addEventListener('click', e => {{
  const g = e.target.closest('.parca'); if (g) return parcaSec(g);
  const d = e.target.closest('.delik'); if (d) return agSec(d.dataset.ag, d.dataset.d);
  temizle();
}});
svg.addEventListener('keydown', e => {{ if ((e.key === 'Enter' || e.key === ' ') && e.target.closest('.parca')) {{ e.preventDefault(); parcaSec(e.target.closest('.parca')); }} }});
document.querySelectorAll('.kat-btn').forEach(b => b.addEventListener('click', () => {{
  const acik = b.getAttribute('aria-pressed') === 'true';
  temizle(); document.querySelectorAll('.kat-btn').forEach(x => x.setAttribute('aria-pressed', 'false'));
  if (acik) {{ baslik.textContent = 'Bir parça seçin'; detay.hidden = true; return; }}
  b.setAttribute('aria-pressed', 'true'); svg.classList.add('odak');
  svg.querySelectorAll('.parca.kat-' + b.dataset.kat).forEach(g => g.classList.add('secik'));
  baslik.textContent = b.querySelector('b').textContent; metin.textContent = b.querySelector('small').textContent;
  detay.hidden = true;
}}));
</script>
"""


if __name__ == "__main__":
    ag = dogrula()
    cikti = Path(__file__).parent / "breadboard.html"
    cikti.write_text(html(svg_cizim(ag), ag), encoding="utf-8")
    print(f"Yazıldı: {cikti}")
