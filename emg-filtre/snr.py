"""SNR hesaplama yardımcıları (benzetim ve gerçek ölçüm için ortak)."""

from __future__ import annotations

import numpy as np
from scipy import signal


def guc(x) -> float:
    x = np.asarray(x, dtype=float)
    return float(np.mean((x - np.mean(x)) ** 2))


def snr_bilinen(temiz, gozlenen) -> float:
    """Temiz sinyal biliniyorsa (benzetim): SNR = 10 log10(P_sinyal / P_gürültü)."""
    gurultu = np.asarray(gozlenen) - np.asarray(temiz)
    return 10 * np.log10(guc(temiz) / guc(gurultu))


def snr_kasilma_dinlenme(x, kas_maske, dinlenme_maske) -> float:
    """Gerçek ölçüm için SNR.

    Kas gevşekken kaydedilen her şey gürültüdür: P_gürültü = P_dinlenme.
    Kasılma sırasında ölçülen güç sinyal + gürültüdür:  P_sinyal = P_kas - P_dinlenme.
    SNR = 10 log10((P_kas - P_dinlenme) / P_dinlenme)
    """
    x = np.asarray(x, dtype=float)
    p_kas = guc(x[kas_maske])
    p_din = guc(x[dinlenme_maske])
    if p_kas <= p_din:
        return float("-inf")
    return 10 * np.log10((p_kas - p_din) / p_din)


def zarf(x, fs: float, kesim: float = 5.0):
    """Doğrultma + 5 Hz alçak geçiren: 'kas kasılma grafiği' (lineer zarf)."""
    sos = signal.butter(2, kesim, fs=fs, output="sos")
    return signal.sosfiltfilt(sos, np.abs(np.asarray(x) - np.mean(x)))


def rms_zarf(x, fs: float, pencere_s: float = 0.1):
    n = max(1, int(pencere_s * fs))
    x = np.asarray(x, dtype=float) - np.mean(x)
    return np.sqrt(np.convolve(x**2, np.ones(n) / n, mode="same"))


def otomatik_bolgeler(x, fs: float):
    """RMS zarfına göre kasılma ve dinlenme bölgelerini otomatik bulur."""
    e = rms_zarf(x, fs)
    alt, ust = np.percentile(e, 10), np.percentile(e, 95)
    kas = e > alt + 0.5 * (ust - alt)
    dinlenme = e < alt + 0.1 * (ust - alt)
    # Geçiş bölgelerini dışarıda bırakmak için maskeleri biraz daralt
    n = int(0.15 * fs)
    k = np.ones(n)
    kas = np.convolve(~kas, k, mode="same") == 0
    dinlenme = np.convolve(~dinlenme, k, mode="same") == 0
    return kas, dinlenme
