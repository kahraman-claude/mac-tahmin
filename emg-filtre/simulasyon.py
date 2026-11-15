"""
EMG benzetimi: tasarlanan analog filtre zincirinin bilgisayarda denenmesi.

Gerçekçi bir yapay EMG sinyali üretilir, üzerine projede belirtilen
parazitler eklenir ve devre.py'deki filtre zincirinden geçirilir.

Çalıştır:  python simulasyon.py                # şekiller + SNR tablosu
           python simulasyon.py --csv ornek.csv # osiloskop benzeri CSV de üret
Çıktılar:  sekiller/sim_zaman.png, sekiller/sim_yakin.png, sekiller/sim_frekans.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

import devre
import snr

SEKIL = Path(__file__).parent / "sekiller"
SEKIL.mkdir(exist_ok=True)

FS = 20_000.0   # Hz - analog devreyi taklit etmek için yüksek örnekleme
SURE = 6.0      # s
KASILMALAR = [(1.0, 2.2), (3.2, 4.8)]  # (başlangıç, bitiş) saniye


def kasilma_zarfi(t):
    """Yumuşak yükselip inen kasılma şiddeti (0..1)."""
    z = np.full_like(t, 0.02)  # gevşek kasın küçük tonus aktivitesi
    for t0, t1 in KASILMALAR:
        yukselis = 0.5 * (1 + np.tanh((t - t0) / 0.06))
        dusus = 0.5 * (1 - np.tanh((t - t1) / 0.08))
        z = np.maximum(z, yukselis * dusus)
    return z


def temiz_emg(t, rng):
    """Bant sınırlı gürültü x kasılma zarfı. Spektrum ~50-150 Hz civarında tepe yapar."""
    w = rng.standard_normal(t.size)
    sos = signal.butter(2, [30, 300], btype="bandpass", fs=FS, output="sos")
    emg = signal.sosfilt(sos, w)
    emg *= kasilma_zarfi(t)
    # Kasılma sırasındaki RMS ~0.5 mV olsun (yüzey EMG için tipik)
    maske = kasilma_zarfi(t) > 0.9
    emg *= 0.5 / np.sqrt(np.mean(emg[maske] ** 2))
    return emg  # mV


def parazitler(t, rng):
    """Projede sayılan parazitler (mV, elektrot girişinde)."""
    p = {}
    # 1) Şebeke gürültüsü: 50 Hz ve harmonikleri (frekans hafifçe dalgalanır)
    faz = 2 * np.pi * np.cumsum(50.0 + 0.05 * np.sin(2 * np.pi * 0.2 * t)) / FS
    p["Şebeke 50 Hz (temel)"] = 0.8 * np.sin(faz)
    p["Şebeke harmonik 150/250"] = 0.12 * np.sin(3 * faz + 0.4) + 0.05 * np.sin(5 * faz + 1.1)
    # 2) Hareket kaynaklı taban kayması (elektrot-deri arayüzü, < 5 Hz)
    p["Hareket / taban kayması"] = 0.6 * np.sin(2 * np.pi * 0.4 * t) + 0.3 * np.sin(2 * np.pi * 1.3 * t + 1)
    # 3) Ani parazitler: kablo çarpması / elektrot teması (kısa darbeler)
    ani = np.zeros_like(t)
    for t0 in rng.uniform(0.3, SURE - 0.3, 7):
        n0, n = int(t0 * FS), int(0.0015 * FS)
        ani[n0:n0 + n] += rng.choice([-1, 1]) * 1.5 * np.sin(np.pi * np.arange(n) / n)
    p["Ani parazitler"] = ani
    # 4) Yüksek frekanslı çevresel gürültü: geniş bant + anahtarlamalı güç kaynağı tonu
    p["Yüksek frekans gürültü"] = 0.15 * rng.standard_normal(t.size) + 0.15 * np.sin(2 * np.pi * 2300 * t)
    return p


def welch(x):
    f, P = signal.welch(x, fs=FS, nperseg=int(FS))  # 1 Hz çözünürlük
    return f, P


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="Osiloskop formatında örnek CSV yaz (zaman, ham_V, filtreli_V)")
    ap.add_argument("--tohum", type=int, default=7)
    args = ap.parse_args()

    rng = np.random.default_rng(args.tohum)
    t = np.arange(0, SURE, 1 / FS)
    emg = temiz_emg(t, rng)
    gurultuler = parazitler(t, rng)
    ham = emg + sum(gurultuler.values())

    # Analog zinciri uygula (giriş seviyesine normalize: çıkış = bu x toplam kazanç)
    sos = devre.ayrik_sos(FS, kazanc_dahil=False)
    filtreli = signal.sosfilt(sos, ham)
    emg_filtreli = signal.sosfilt(sos, emg)  # aynı filtreden geçen 'ideal' sinyal

    # İlk 0.5 s'yi (filtre geçici rejimi) değerlendirmeye alma
    gecerli = t > 0.5
    kas_m = (kasilma_zarfi(t) > 0.95) & gecerli
    din_m = (kasilma_zarfi(t) < 0.03) & gecerli

    print("=" * 66)
    print(" BENZETİM SONUÇLARI (giriş seviyesinde, mV)")
    print("=" * 66)
    print(f" Temiz EMG RMS (kasılma)            : {np.sqrt(np.mean(emg[kas_m]**2)):.3f} mV")
    for isim, g in gurultuler.items():
        g_f = signal.sosfilt(sos, g)
        print(f" {isim:<26} RMS: önce {np.sqrt(snr.guc(g[gecerli])):.3f} mV -> "
              f"sonra {np.sqrt(snr.guc(g_f[gecerli])):.3f} mV  "
              f"({10*np.log10(snr.guc(g[gecerli])/snr.guc(g_f[gecerli])):5.1f} dB bastırma)")
    print("-" * 66)
    s1 = snr.snr_bilinen(emg[gecerli], ham[gecerli])
    s2 = snr.snr_bilinen(emg_filtreli[gecerli], filtreli[gecerli])
    print(f" SNR (temiz sinyal biliniyor)     : önce {s1:6.1f} dB  ->  sonra {s2:6.1f} dB   "
          f"(kazanç {s2 - s1:+.1f} dB)")
    s3 = snr.snr_kasilma_dinlenme(ham, kas_m, din_m)
    s4 = snr.snr_kasilma_dinlenme(filtreli, kas_m, din_m)
    print(f" SNR (kasılma / dinlenme yöntemi) : önce {s3:6.1f} dB  ->  sonra {s4:6.1f} dB   "
          f"(kazanç {s4 - s3:+.1f} dB)")
    print("   * İkinci yöntem gerçek osiloskop kaydında kullanılacak olandır (olcum_analiz.py).")
    print("=" * 66)

    G = devre.toplam_kazanc()
    zarf_f = snr.zarf(filtreli, FS)
    zarf_h = snr.zarf(ham, FS)

    # ---------------- Şekil 1: zaman düzlemi ----------------
    fig, ax = plt.subplots(4, 1, figsize=(11, 10), sharex=True)
    ax[0].plot(t, emg, color="#2ca02c", lw=0.5)
    ax[0].set_title("(a) Temiz kas sinyali (benzetimde bilinen referans)")
    ax[1].plot(t, ham, color="#7f7f7f", lw=0.5)
    ax[1].set_title(f"(b) Ham sinyal — filtresiz (SNR = {s3:.1f} dB)")
    ax[2].plot(t, filtreli, color="#1f77b4", lw=0.5)
    ax[2].set_title(f"(c) Filtrelenmiş sinyal (SNR = {s4:.1f} dB)")
    sag = ax[2].twinx()
    sag.set_ylim(np.array(ax[2].get_ylim()) * G / 1000)
    sag.set_ylabel("Devre çıkışı (V)")
    ax[3].plot(t, zarf_h, color="#7f7f7f", lw=1.5, label="Ham sinyalden")
    ax[3].plot(t, zarf_f, color="#d62728", lw=2, label="Filtrelenmiş sinyalden")
    ax[3].set_title("(d) Kas kasılma grafiği (doğrultulmuş + 5 Hz yumuşatılmış zarf)")
    ax[3].legend(loc="upper right")
    for a in ax:
        a.set_ylabel("mV (giriş)")
        a.grid(alpha=0.3)
        for t0, t1 in KASILMALAR:
            a.axvspan(t0, t1, color="gold", alpha=0.12)
    ax[3].set_xlabel("Zaman (s)   —   sarı bölgeler: kasılma")
    fig.tight_layout()
    fig.savefig(SEKIL / "sim_zaman.png", dpi=130)
    plt.close(fig)

    # ---------------- Şekil 2: yakın görünüm ----------------
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
    for a, (t0, baslik) in zip(ax, [(0.55, "Kas gevşek (0.55–0.75 s)"), (1.6, "Kas kasılı (1.60–1.80 s)")]):
        m = (t >= t0) & (t < t0 + 0.2)
        a.plot(t[m], ham[m], color="#7f7f7f", lw=0.8, label="Ham")
        a.plot(t[m], filtreli[m], color="#1f77b4", lw=1.2, label="Filtrelenmiş")
        a.set_title(baslik)
        a.set_xlabel("Zaman (s)")
        a.grid(alpha=0.3)
        a.legend(loc="upper right")
    ax[0].set_ylabel("mV (giriş)")
    fig.suptitle("Yakın görünüm: gevşekken ham sinyalde 50 Hz dalgası baskın; filtre sonrası küçük bir kalıntı kalıyor")
    fig.tight_layout()
    fig.savefig(SEKIL / "sim_yakin.png", dpi=130)
    plt.close(fig)

    # ---------------- Şekil 3: frekans düzlemi ----------------
    f, P_ham = welch(ham[gecerli])
    _, P_fil = welch(filtreli[gecerli])
    _, P_emg = welch(emg[gecerli])
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.semilogx(f[1:], 10 * np.log10(P_ham[1:]), color="#7f7f7f", lw=1, label="Ham")
    ax.semilogx(f[1:], 10 * np.log10(P_fil[1:]), color="#1f77b4", lw=1.3, label="Filtrelenmiş")
    ax.semilogx(f[1:], 10 * np.log10(P_emg[1:]), color="#2ca02c", lw=1, ls="--", label="Temiz EMG (referans)")
    for fx, yazi in [(50, "50 Hz"), (150, "150 Hz"), (2300, "2.3 kHz")]:
        ax.annotate(yazi, (fx, 10 * np.log10(P_ham[int(fx)])), textcoords="offset points",
                    xytext=(5, 5), fontsize=9)
    ax.set_xlim(0.5, FS / 2)
    ax.set_ylim(-110, 0)
    ax.set_xlabel("Frekans (Hz)")
    ax.set_ylabel("Güç spektral yoğunluğu (dB mV²/Hz)")
    ax.set_title("Frekans düzlemi karşılaştırması (Welch)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(SEKIL / "sim_frekans.png", dpi=130)
    plt.close(fig)

    print(f"Şekiller: {SEKIL}/sim_zaman.png, sim_yakin.png, sim_frekans.png")

    if args.csv:
        adim = 4  # 20 kHz -> 5 kHz (osiloskop kaydı gibi)
        ham_v = ham * devre.ina_kazanci() / 1000          # TP1: INA çıkışı (V)
        fil_v = filtreli * G / 1000                         # TP4: devre çıkışı (V)
        veri = np.column_stack([t, ham_v, fil_v])[::adim]
        np.savetxt(args.csv, veri, delimiter=",", fmt="%.6g",
                   header="zaman_s,ham_V,filtreli_V", comments="")
        print(f"Örnek osiloskop CSV'si yazıldı: {args.csv}")


if __name__ == "__main__":
    main()
