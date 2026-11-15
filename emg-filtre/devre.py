"""
EMG filtre devresinin bileşen değerleri ve katların transfer fonksiyonları.

Sinyal zinciri:
  Elektrotlar -> [1] Enstrümantasyon yükselteci (AD620, G~50)
              -> [2] Aktif Twin-T çentik filtre (50 Hz, Q~2.5)      LM324 A + B
              -> [3] Sallen-Key alçak geçiren (2. derece, ~480 Hz)  LM324 C
              -> [4] Yüksek geçiren (~19 Hz) + kazanç katı (x13)    LM324 D
              -> Osiloskop

Tüm dirençler kolay bulunan E24 serisindendir (gerekirse iki direnç seri).
Benzetim ve ölçüm analizi bu dosyadaki değerleri kullanır; devrede bir değeri
değiştirirseniz burada da değiştirin.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import signal

SEBEKE_FREKANSI = 50.0  # Hz (Türkiye)


# --------------------------------------------------------------------------
# Bileşen değerleri
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Degerler:
    # [1] AD620: G = 1 + 49.4k / RG
    RG: float = 1.0e3

    # [4] Yüksek geçiren RC (kazanç katının girişinde): fc = 1 / (2*pi*R*C)
    R_hp: float = 8.2e3
    C_hp: float = 1.0e-6

    # [2] Twin-T: seri kollar R, R ve C, C; şönt kollar R/2 ve 2C
    R_tt: float = 31.8e3     # 30k + 1,8k seri
    R_tt_yarim: float = 15.9e3  # devrede 13k + 5k çok turlu trimpot (çentik ayarı)
    C_tt: float = 100e-9     # film kondansatör
    C_tt_cift: float = 200e-9  # 2 x 100 nF paralel
    # Geri besleme bölücü: k = Rb / (Ra + Rb)  ->  Q = 1 / (4 (1 - k))
    Ra_tt: float = 1.0e3
    Rb_tt: float = 9.1e3

    # [3] Sallen-Key eşit elemanlı: f = 1/(2*pi*R*C), K = 1 + Rf/Rg, Q = 1/(3-K)
    R_sk: float = 33e3
    C_sk: float = 10e-9
    Rf_sk: float = 5.6e3
    Rg_sk: float = 10e3

    # [4] Evirmeyen kazanç katı: G = 1 + Rf/Rg
    Rf_g: float = 120e3
    Rg_g: float = 10e3


D = Degerler()


# --------------------------------------------------------------------------
# Türetilmiş büyüklükler
# --------------------------------------------------------------------------
def ina_kazanci(d: Degerler = D) -> float:
    return 1.0 + 49.4e3 / d.RG


def hp_kesim(d: Degerler = D) -> float:
    return 1.0 / (2 * math.pi * d.R_hp * d.C_hp)


def centik_merkez(d: Degerler = D) -> float:
    return 1.0 / (2 * math.pi * d.R_tt * d.C_tt)


def centik_k(d: Degerler = D) -> float:
    return d.Rb_tt / (d.Ra_tt + d.Rb_tt)


def centik_Q(d: Degerler = D) -> float:
    return 1.0 / (4.0 * (1.0 - centik_k(d)))


def ag_kesim(d: Degerler = D) -> float:
    return 1.0 / (2 * math.pi * d.R_sk * d.C_sk)


def ag_K(d: Degerler = D) -> float:
    return 1.0 + d.Rf_sk / d.Rg_sk


def ag_Q(d: Degerler = D) -> float:
    return 1.0 / (3.0 - ag_K(d))


def son_kazanc(d: Degerler = D) -> float:
    return 1.0 + d.Rf_g / d.Rg_g


def toplam_kazanc(d: Degerler = D) -> float:
    """Geçirme bandındaki toplam kazanç (INA x Sallen-Key K x son kat)."""
    return ina_kazanci(d) * ag_K(d) * son_kazanc(d)


# --------------------------------------------------------------------------
# Sürekli zaman transfer fonksiyonları (pay, payda) - s düzleminde
# --------------------------------------------------------------------------
def tf_hp(d: Degerler = D):
    wh = 2 * math.pi * hp_kesim(d)
    return [1.0, 0.0], [1.0, wh]


def tf_centik(d: Degerler = D):
    """İdeal (eşleşmiş) aktif Twin-T: (s^2 + w0^2) / (s^2 + 4(1-k) w0 s + w0^2)."""
    w0 = 2 * math.pi * centik_merkez(d)
    return [1.0, 0.0, w0**2], [1.0, w0 / centik_Q(d), w0**2]


def tf_ag(d: Degerler = D):
    wc = 2 * math.pi * ag_kesim(d)
    return [ag_K(d) * wc**2], [1.0, wc / ag_Q(d), wc**2]


def katlar(d: Degerler = D, kazanc_dahil: bool = True):
    """(isim, pay, payda) listesi. kazanc_dahil=False ise zincir 0 dB'e normalize edilir."""
    liste = [
        ("Yüksek geçiren", *tf_hp(d)),
        ("Çentik (50 Hz)", *tf_centik(d)),
        ("Alçak geçiren", *tf_ag(d)),
    ]
    if kazanc_dahil:
        liste.insert(0, ("INA kazancı", [ina_kazanci(d)], [1.0]))
        liste.append(("Son kazanç", [son_kazanc(d)], [1.0]))
    else:
        # Alçak geçirenin K kazancını da çıkar ki zincir giriş seviyesinde kalsın
        b, a = tf_ag(d)
        liste[2] = ("Alçak geçiren", [b[0] / ag_K(d)], a)
    return liste


def zincir_tf(d: Degerler = D, kazanc_dahil: bool = True):
    b, a = np.array([1.0]), np.array([1.0])
    for _, bb, aa in katlar(d, kazanc_dahil):
        b = np.polymul(b, bb)
        a = np.polymul(a, aa)
    return b, a


def ayrik_sos(fs: float, d: Degerler = D, kazanc_dahil: bool = False):
    """Analog zinciri fs örnekleme frekansında bilinear dönüşümle ayrıklaştırır.

    Benzetimde analog devrenin davranışını taklit etmek için kullanılır.
    Her kat ayrı ayrı (ön bükme ile) dönüştürülür; böylece 50 Hz çentik
    ve kesim frekansları tam yerinde kalır.
    """
    soslar = []
    kritik = {"Yüksek geçiren": hp_kesim(d), "Çentik (50 Hz)": centik_merkez(d),
              "Alçak geçiren": ag_kesim(d)}
    for isim, b, a in katlar(d, kazanc_dahil):
        if len(a) == 1:  # saf kazanç
            soslar.append(np.array([[b[0] / a[0], 0, 0, 1, 0, 0]]))
            continue
        z, p, k = signal.tf2zpk(b, a)
        # Ön bükme: kritik frekansta analog ve sayısal yanıt aynı olsun
        f0 = kritik[isim]
        w_analog = 2 * math.pi * f0
        w_dijital = 2 * fs * math.tan(math.pi * f0 / fs)
        olcek = w_dijital / w_analog
        z2, p2, k2 = np.asarray(z) * olcek, np.asarray(p) * olcek, k * olcek ** (len(p) - len(z))
        zd, pd, kd = signal.bilinear_zpk(z2, p2, k2, fs)
        soslar.append(signal.zpk2sos(zd, pd, kd))
    return np.vstack(soslar)


# --------------------------------------------------------------------------
# Gerçek Twin-T ağı (eleman toleranslarını görmek için düğüm analizi)
# --------------------------------------------------------------------------
def twin_t_yanit(f, R1, R2, R3, C1, C2, C3, k):
    """Aktif Twin-T'nin düğüm analiziyle tam frekans yanıtı.

    Kol 1: Vi --R1-- A --R2-- Vo ,  A --C3(2C)-- Vf
    Kol 2: Vi --C1-- B --C2-- Vo ,  B --R3(R/2)-- Vf
    Vo bir gerilim izleyiciye girer (akım çekmez); Vf = k * Vo (bölücü + izleyici).
    """
    f = np.atleast_1d(np.asarray(f, dtype=float))
    s = 1j * 2 * np.pi * f
    H = np.empty_like(s)
    g1, g2, g3 = 1 / R1, 1 / R2, 1 / R3
    for i, si in enumerate(s):
        y1, y2, y3 = si * C1, si * C2, si * C3
        # Bilinmeyenler: [A, B, Vo], Vi = 1
        M = np.array([
            [g1 + g2 + y3, 0, -g2 - y3 * k],          # A düğümü
            [0, y1 + y2 + g3, -y2 - g3 * k],          # B düğümü
            [g2, y2, -(g2 + y2)],                     # Vo düğümü (akım yok)
        ], dtype=complex)
        rhs = np.array([g1, y1, 0], dtype=complex)
        A_, B_, Vo = np.linalg.solve(M, rhs)
        H[i] = Vo
    return H
