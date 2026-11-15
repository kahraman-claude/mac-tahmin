"""
Filtre tasarım hesapları.

Çalıştır:  python tasarim_hesap.py
Çıktılar:  ekrana hesap tablosu, sekiller/bode.png, sekiller/centik_tolerans.png
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

import devre
from devre import D

SEKIL = Path(__file__).parent / "sekiller"
SEKIL.mkdir(exist_ok=True)


def db(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-12))


def yanit(b, a, f):
    _, h = signal.freqs(b, a, worN=2 * np.pi * f)
    return h


def hesap_tablosu():
    print("=" * 66)
    print(" EMG FİLTRE DEVRESİ - TASARIM HESAPLARI")
    print("=" * 66)
    print(f"[1] Enstrümantasyon yükselteci (AD620)")
    print(f"    G = 1 + 49.4k / RG = 1 + 49.4k / {D.RG/1e3:.1f}k = {devre.ina_kazanci():.1f}")
    print(f"[2] Yüksek geçiren (1. derece RC)")
    print(f"    fc = 1/(2*pi*R*C) = 1/(2*pi*{D.R_hp/1e3:.1f}k*{D.C_hp*1e6:.0f}uF) = {devre.hp_kesim():.1f} Hz")
    print(f"[3] Aktif Twin-T çentik")
    print(f"    f0 = 1/(2*pi*R*C) = 1/(2*pi*{D.R_tt/1e3:.1f}k*{D.C_tt*1e9:.0f}nF) = {devre.centik_merkez():.2f} Hz")
    print(f"    k  = Rb/(Ra+Rb) = {D.Rb_tt/1e3:.1f}k/({D.Ra_tt/1e3:.1f}k+{D.Rb_tt/1e3:.1f}k) = {devre.centik_k():.3f}")
    print(f"    Q  = 1/(4(1-k)) = {devre.centik_Q():.2f}   ->  -3 dB bant genişliği = f0/Q = "
          f"{devre.centik_merkez()/devre.centik_Q():.1f} Hz")
    print(f"[4] Sallen-Key alçak geçiren (eşit elemanlı, 2. derece Butterworth)")
    print(f"    fc = 1/(2*pi*R*C) = 1/(2*pi*{D.R_sk/1e3:.0f}k*{D.C_sk*1e9:.0f}nF) = {devre.ag_kesim():.0f} Hz")
    print(f"    K  = 1 + Rf/Rg = 1 + {D.Rf_sk/1e3:.2f}k/{D.Rg_sk/1e3:.0f}k = {devre.ag_K():.3f}"
          f"   (Butterworth için 3 - sqrt(2) = 1.586)")
    print(f"    Q  = 1/(3-K) = {devre.ag_Q():.3f}   (Butterworth için 0.707)")
    print(f"[5] Son kazanç katı (evirmeyen)")
    print(f"    G = 1 + {D.Rf_g/1e3:.0f}k/{D.Rg_g/1e3:.0f}k = {devre.son_kazanc():.1f}")
    print("-" * 66)
    G = devre.toplam_kazanc()
    print(f"    Toplam kazanç = {devre.ina_kazanci():.1f} x {devre.ag_K():.3f} x {devre.son_kazanc():.0f}"
          f" = {G:.0f}  ({20*math.log10(G):.1f} dB)")
    print(f"    1 mV'lik kas sinyali çıkışta ~{G/1000:.2f} V olarak görünür.")

    # Zincirin önemli frekanslardaki zayıflatması (0 dB'e normalize)
    b, a = devre.zincir_tf(kazanc_dahil=False)
    print("-" * 66)
    print("    Normalize zincir yanıtı (geçirme bandı = 0 dB):")
    for f in [1, 10, 20, 50, 100, 150, 250, 480, 1000, 2000, 5000]:
        print(f"      {f:>5} Hz : {db(yanit(b, a, np.array([f])))[0]:7.1f} dB")
    print("=" * 66)


def bode_ciz():
    f = np.logspace(0, 4, 2000)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    renkler = {"Yüksek geçiren": "#1f77b4", "Çentik (50 Hz)": "#d62728", "Alçak geçiren": "#2ca02c"}
    for isim, b, a in devre.katlar(kazanc_dahil=False):
        h = yanit(b, a, f)
        ax1.semilogx(f, db(h), "--", lw=1.3, color=renkler[isim], label=isim)
    b, a = devre.zincir_tf(kazanc_dahil=False)
    h = yanit(b, a, f)
    ax1.semilogx(f, db(h), "k", lw=2.2, label="Toplam zincir")
    ax1.axvspan(20, 450, color="gold", alpha=0.15, label="EMG bandı (20–450 Hz)")
    ax1.axvline(50, color="gray", lw=0.8, ls=":")
    ax1.set_ylim(-60, 6)
    ax1.set_ylabel("Kazanç (dB, normalize)")
    ax1.set_title(f"Filtre zinciri frekans yanıtı  —  toplam geçirme bandı kazancı ≈ "
                  f"{devre.toplam_kazanc():.0f} ({20*np.log10(devre.toplam_kazanc()):.0f} dB)")
    ax1.grid(True, which="both", alpha=0.3)
    ax1.legend(loc="lower center", ncol=3, fontsize=9)

    ax2.semilogx(f, np.degrees(np.unwrap(np.angle(h))), "k", lw=1.8)
    ax2.set_ylabel("Faz (derece)")
    ax2.set_xlabel("Frekans (Hz)")
    ax2.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(SEKIL / "bode.png", dpi=130)
    plt.close(fig)


def tolerans_analizi(n: int = 2000, seed: int = 1):
    """Twin-T'nin eleman toleranslarına duyarlılığı (Monte Carlo)."""
    rng = np.random.default_rng(seed)
    f = np.linspace(30, 75, 900)
    k = devre.centik_k()

    # Önce düğüm analizinin ideal formülle uyuştuğunu kontrol et
    ideal = devre.twin_t_yanit(f, D.R_tt, D.R_tt, D.R_tt / 2, D.C_tt, D.C_tt, 2 * D.C_tt, k)
    b, a = devre.tf_centik()
    formul = yanit(b, a, f)
    assert np.max(np.abs(ideal - formul)) < 1e-6, "Düğüm analizi ideal formülle uyuşmuyor"

    senaryolar = {"Direnç %1, kondansatör %5": (0.01, 0.05),
                  "Direnç %1, kondansatör %1 (seçilmiş)": (0.01, 0.01)}
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    print("\n Twin-T tolerans analizi (Monte Carlo, 50 Hz'deki bastırma):")
    for ax, (isim, (tr, tc)) in zip(axes, senaryolar.items()):
        bastirma = []
        for i in range(n):
            R = D.R_tt * (1 + tr * rng.uniform(-1, 1, 3))
            C = D.C_tt * (1 + tc * rng.uniform(-1, 1, 3))
            h = devre.twin_t_yanit(f, R[0], R[1], D.R_tt_yarim * R[2] / D.R_tt,
                                   C[0], C[1], 2 * C[2], k)
            if i < 60:
                ax.plot(f, db(h), color="#d62728", alpha=0.15, lw=0.8)
            h50 = devre.twin_t_yanit([50.0], R[0], R[1], D.R_tt_yarim * R[2] / D.R_tt,
                                     C[0], C[1], 2 * C[2], k)
            bastirma.append(-db(h50)[0])
        bastirma = np.array(bastirma)
        ax.plot(f, db(ideal), "k", lw=2, label="Nominal değerler")
        ax.set_title(f"{isim}\n50 Hz bastırma: medyan {np.median(bastirma):.0f} dB, "
                     f"en kötü %10: {np.percentile(bastirma, 10):.0f} dB", fontsize=10)
        ax.set_xlabel("Frekans (Hz)")
        ax.grid(alpha=0.3)
        ax.set_ylim(-60, 3)
        ax.legend(loc="lower left")
        print(f"   {isim:<40}: medyan {np.median(bastirma):5.1f} dB, "
              f"%10'luk dilim {np.percentile(bastirma, 10):5.1f} dB")
    axes[0].set_ylabel("Kazanç (dB)")
    fig.suptitle("Twin-T çentik: eleman toleranslarının etkisi (R/2 kolundaki trimpot ile derinlik geri kazanılır)",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(SEKIL / "centik_tolerans.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    hesap_tablosu()
    bode_ciz()
    tolerans_analizi()
    print(f"\nŞekiller kaydedildi: {SEKIL}/bode.png, {SEKIL}/centik_tolerans.png")
