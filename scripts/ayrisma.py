"""
Model ile piyasa ayrıştığında kim haklı?

Her maçın her sonucu (ev / beraberlik / deplasman) için iki olasılık var:
    p_model  : modelin olasılığı
    p_piyasa : bahis oranlarından hesaplanan, favori–sürpriz yanlılığı düzeltilmiş piyasa olasılığı
    fark     = p_model − p_piyasa

fark ≥ +ESIK  → model bu sonuca piyasadan belirgin şekilde DAHA ÇOK olasılık vermiş ("model daha iyimser")
fark ≤ −ESIK  → model bu sonuca piyasadan belirgin şekilde DAHA AZ olasılık vermiş ("model daha kötümser")

Her grupta üç sayı karşılaştırılır: modelin ortalama olasılığı, piyasanın ortalama olasılığı ve sonucun
gerçekleşme oranı. Gerçekleşme oranı hangisine yakınsa, ayrışmalarda o taraf haklı çıkmış demektir.
"""
import numpy as np

ESIK = 0.10


def ayrisma_ozeti(Pm, Pp, y, esik=ESIK):
    Pm, Pp, y = np.asarray(Pm, float), np.asarray(Pp, float), np.asarray(y, int)
    g = np.eye(3)[y]
    fark = Pm - Pp
    sonuc = {"esik": esik, "n_mac": int(len(y))}
    for ad, maske in (("model_iyimser", fark >= esik), ("model_kotumser", fark <= -esik)):
        n = int(maske.sum())
        sonuc[ad] = {"n": n} if n == 0 else {
            "n": n, "model": round(float(Pm[maske].mean()), 4), "piyasa": round(float(Pp[maske].mean()), 4),
            "gercek": round(float(g[maske].mean()), 4),
            "hata_payi": round(float(1.96 * g[maske].std() / np.sqrt(n)), 4)}
    # favorileri farklı olan maçlar
    fm, fp = Pm.argmax(1), Pp.argmax(1)
    f = fm != fp
    sonuc["favori_farkli"] = {"n": int(f.sum())}
    if f.sum():
        sonuc["favori_farkli"].update({
            "model_hakli": round(float(np.mean(fm[f] == y[f])), 4),
            "piyasa_hakli": round(float(np.mean(fp[f] == y[f])), 4)})
    return sonuc
