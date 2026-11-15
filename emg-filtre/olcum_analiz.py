"""
Gerçek osiloskop kaydının analizi: filtre öncesi / sonrası karşılaştırma ve SNR.

Osiloskopta iki kanalı aynı anda kaydedin ve CSV olarak dışa aktarın:
  CH1 = TP1 (AD620 çıkışı, filtresiz ham sinyal)
  CH2 = TP4 (devre çıkışı, filtrelenmiş sinyal)
Kayıt sırasında kası birkaç kez kasıp gevşetin (her biri ~1-2 s).

Kullanım:
  python olcum_analiz.py kayit.csv
  python olcum_analiz.py kayit.csv --zaman 0 --ham 1 --filtreli 2
  python olcum_analiz.py kayit.csv --dinlenme 0:0.8 --kasilma 1.2:2.0
  python olcum_analiz.py kayit.csv --fs 5000          # zaman sütunu yoksa / örnek no ise

Sütun numaraları 0'dan başlar. Başlık/birim satırları otomatik atlanır.
Kasılma ve dinlenme bölgeleri verilmezse filtrelenmiş sinyalden otomatik bulunur.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

import devre
import snr


def csv_oku(yol: str, sutunlar: list[int]) -> np.ndarray:
    satirlar = []
    with open(yol, newline="", encoding="utf-8", errors="ignore") as f:
        ornek = f.read(4096)
        f.seek(0)
        ayrac = ";" if ornek.count(";") > ornek.count(",") else ","
        for s in csv.reader(f, delimiter=ayrac):
            try:
                satirlar.append([float(s[i].replace(" ", "")) for i in sutunlar])
            except (ValueError, IndexError):
                continue  # başlık, birim veya boş satır
    if len(satirlar) < 100:
        raise SystemExit(f"{yol}: yeterli sayısal satır bulunamadı ({len(satirlar)}). "
                         "Sütun numaralarını --zaman/--ham/--filtreli ile kontrol edin.")
    return np.array(satirlar)


def aralik(metin: str | None, t: np.ndarray):
    if not metin:
        return None
    m = np.zeros_like(t, dtype=bool)
    for parca in metin.split(","):
        a, b = (float(x) for x in parca.split(":"))
        m |= (t >= a) & (t < b)
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--zaman", type=int, default=0, help="zaman sütunu (varsayılan 0)")
    ap.add_argument("--ham", type=int, default=1, help="ham sinyal sütunu (varsayılan 1)")
    ap.add_argument("--filtreli", type=int, default=2, help="filtreli sinyal sütunu (varsayılan 2)")
    ap.add_argument("--fs", type=float, help="örnekleme frekansı (Hz); verilirse zaman sütunu yok sayılır")
    ap.add_argument("--kazanc-ham", type=float, default=devre.ina_kazanci(),
                    help="TP1'deki kazanç (varsayılan AD620 kazancı)")
    ap.add_argument("--kazanc-filtreli", type=float, default=devre.toplam_kazanc(),
                    help="TP4'teki toplam kazanç")
    ap.add_argument("--kasilma", help="kasılma aralıkları, örn. 1.2:2.0,3.5:4.4 (s)")
    ap.add_argument("--dinlenme", help="dinlenme aralıkları, örn. 0:0.8 (s)")
    ap.add_argument("--cikti", default=None, help="şekil klasörü (varsayılan: CSV'nin yanında)")
    args = ap.parse_args()

    veri = csv_oku(args.csv, [args.zaman, args.ham, args.filtreli])
    if args.fs:
        fs = args.fs
        t = np.arange(len(veri)) / fs
    else:
        t = veri[:, 0] - veri[0, 0]
        fs = 1.0 / np.median(np.diff(t))
    # Volt -> giriş seviyesinde mV (iki kanal aynı ölçekte karşılaştırılsın)
    ham = (veri[:, 1] - veri[:, 1].mean()) / args.kazanc_ham * 1000
    fil = (veri[:, 2] - veri[:, 2].mean()) / args.kazanc_filtreli * 1000

    kas = aralik(args.kasilma, t)
    din = aralik(args.dinlenme, t)
    if kas is None or din is None:
        k_oto, d_oto = snr.otomatik_bolgeler(fil, fs)
        kas = k_oto if kas is None else kas
        din = d_oto if din is None else din
    if kas.sum() < fs * 0.2 or din.sum() < fs * 0.2:
        raise SystemExit("Kasılma/dinlenme bölgeleri bulunamadı; --kasilma ve --dinlenme ile elle verin.")

    s_ham = snr.snr_kasilma_dinlenme(ham, kas, din)
    s_fil = snr.snr_kasilma_dinlenme(fil, kas, din)

    f, P_ham = signal.welch(ham, fs=fs, nperseg=min(len(ham), int(fs)))
    _, P_fil = signal.welch(fil, fs=fs, nperseg=min(len(fil), int(fs)))
    i50 = np.argmin(np.abs(f - 50))
    bastirma_50 = 10 * np.log10(P_ham[i50] / P_fil[i50])

    print("=" * 60)
    print(f" Dosya          : {args.csv}")
    print(f" Örnekleme      : {fs:.0f} Hz, süre {t[-1]:.2f} s, {len(t)} örnek")
    print(f" Kasılma süresi : {kas.sum()/fs:.2f} s, dinlenme süresi: {din.sum()/fs:.2f} s")
    print(f" SNR ham        : {s_ham:6.1f} dB")
    print(f" SNR filtreli   : {s_fil:6.1f} dB")
    print(f" SNR iyileşmesi : {s_fil - s_ham:+6.1f} dB")
    print(f" 50 Hz bastırma : {bastirma_50:6.1f} dB (spektrumdan)")
    print("=" * 60)

    cikti = Path(args.cikti) if args.cikti else Path(args.csv).with_suffix("")
    cikti.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(3, 1, figsize=(11, 8.5), sharex=True)
    ax[0].plot(t, ham, color="#7f7f7f", lw=0.5)
    ax[0].set_title(f"Ham sinyal (TP1)  —  SNR = {s_ham:.1f} dB")
    ax[1].plot(t, fil, color="#1f77b4", lw=0.5)
    ax[1].set_title(f"Filtrelenmiş sinyal (TP4)  —  SNR = {s_fil:.1f} dB")
    ax[2].plot(t, snr.zarf(ham, fs), color="#7f7f7f", lw=1.5, label="Ham sinyalden")
    ax[2].plot(t, snr.zarf(fil, fs), color="#d62728", lw=2, label="Filtrelenmiş sinyalden")
    ax[2].set_title("Kas kasılma grafiği (zarf)")
    ax[2].legend(loc="upper right")
    for a in ax:
        a.set_ylabel("mV (giriş)")
        a.grid(alpha=0.3)
        y0, y1 = a.get_ylim()
        a.fill_between(t, y0, y1, where=kas, color="gold", alpha=0.15, lw=0)
        a.fill_between(t, y0, y1, where=din, color="#9ecae1", alpha=0.15, lw=0)
        a.set_ylim(y0, y1)
    ax[2].set_xlabel("Zaman (s)   —   sarı: kasılma, mavi: dinlenme (SNR'de kullanılan bölgeler)")
    fig.tight_layout()
    fig.savefig(cikti / "olcum_zaman.png", dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.semilogx(f[1:], 10 * np.log10(P_ham[1:]), color="#7f7f7f", lw=1, label="Ham (TP1)")
    ax.semilogx(f[1:], 10 * np.log10(P_fil[1:]), color="#1f77b4", lw=1.3, label="Filtrelenmiş (TP4)")
    ax.axvline(50, color="#d62728", lw=0.8, ls=":")
    ax.set_xlabel("Frekans (Hz)")
    ax.set_ylabel("Güç spektral yoğunluğu (dB mV²/Hz)")
    ax.set_title(f"Frekans düzlemi — 50 Hz'de {bastirma_50:.0f} dB bastırma")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(cikti / "olcum_frekans.png", dpi=130)
    plt.close(fig)
    print(f" Şekiller: {cikti}/olcum_zaman.png, olcum_frekans.png")


if __name__ == "__main__":
    main()
