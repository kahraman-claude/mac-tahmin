# Kas Kasılma Grafiği ve EMG Sinyal Filtreleme Projesi

Kas kasıldığında oluşan çok küçük (~0,1–2 mV) elektrik sinyalini yüzey elektrotlarıyla alıp
**50 Hz çentik filtre** ve **alçak geçiren filtre** ile temizleyen, sonucu osiloskopta
gösteren analog devre. Filtrenin başarısı zaman/frekans grafikleri ve **SNR** ile sayısal olarak gösterilir.

Bu klasörde:

| Dosya | İçerik |
|---|---|
| `README.md` | Devre tasarımı, hesaplar, malzeme listesi, deney adımları, güvenlik |
| `devre.py` | Bileşen değerleri ve her katın transfer fonksiyonu (tek kaynak) |
| `tasarim_hesap.py` | Tüm hesapları yazdırır, Bode diyagramı ve tolerans analizini çizer |
| `simulasyon.py` | Yapay EMG + parazitlerle devrenin bilgisayarda denenmesi, SNR |
| `olcum_analiz.py` | Osiloskoptan alınan gerçek kaydın analizi (grafikler + SNR) |
| `snr.py` | SNR ve zarf hesaplama fonksiyonları |
| `sekiller/` | Üretilen grafikler |

```bash
pip install -r requirements.txt
python tasarim_hesap.py        # hesap tablosu + sekiller/bode.png, centik_tolerans.png
python simulasyon.py           # sekiller/sim_zaman.png, sim_yakin.png, sim_frekans.png
python olcum_analiz.py kayit.csv   # gerçek ölçüm
```

---

## 1. Blok diyagram

```
 Elektrotlar        [1]              [2]              [3]               [4]               [5]
 (+)  (−)  (Ref)  AD620 INA   →   Yüksek geçiren  →  Twin-T çentik  →  Sallen-Key AG  →  Kazanç   →  Osiloskop
  │    │    │     G ≈ 50           fc ≈ 19 Hz        f0 = 50 Hz        fc ≈ 480 Hz       x13
  └────┴────┘                      + tampon          Q ≈ 2,5           2. derece BW
                    TP1               TP2               TP3               (K=1,59)          TP4
```

| Kat | Görevi | Neden gerekli |
|---|---|---|
| [1] Enstrümantasyon yükselteci | İki elektrot arasındaki farkı yükseltir, ortak gerilimi (vücuda binen 50 Hz'in büyük kısmı) reddeder | EMG çok küçük; şebeke paraziti iki elektrotta da aynı olduğu için fark alınınca büyük ölçüde yok olur (CMRR) |
| [2] Yüksek geçiren | Elektrot DC ofsetini ve hareketten kaynaklanan yavaş taban kaymasını keser | Aksi halde sonraki katlar doyuma gider |
| [3] Çentik filtre | Fark girişine sızan 50 Hz'i bastırır | Projenin ana hedefi: şebeke gürültüsü |
| [4] Alçak geçiren | 500 Hz üstündeki çevresel gürültüyü keser | EMG'nin faydalı enerjisi 20–450 Hz arasındadır |
| [5] Kazanç | Toplam kazancı ~1000'e çıkarır | 1 mV'lik sinyal osiloskopta ~1 V görünsün |

İlk katın kazancı bilerek düşük (~50) tutuldu: elektrotların DC ofseti onlarca mV olabilir; kazanç
1000 olsaydı AD620 daha ilk katta doyuma giderdi. Kazancın geri kalanı DC kesildikten sonra veriliyor.

---

## 2. Devre ve hesaplar

Tüm değerler `devre.py` içindedir; `python tasarim_hesap.py` aynı hesapları yazdırır.
Besleme: **iki adet 9 V pil** ile ±9 V (orta nokta = devre toprağı).

### [1] Enstrümantasyon yükselteci — AD620

```
 Elektrot (+) ──[10k]──── pin 3 (+IN)
                         pin 1 ─┐
                                RG = 1,0 kΩ
                         pin 8 ─┘
 Elektrot (−) ──[10k]──── pin 2 (−IN)        pin 6 (OUT) ──→ TP1
                         pin 5 (REF) ── GND
 Referans elektrot ──[10k]── GND             pin 7: +9 V, pin 4: −9 V
```

**G = 1 + 49,4 kΩ / RG = 1 + 49,4 / 1,0 = 50,4**

10 kΩ'luk seri dirençler hata durumunda vücuttan akabilecek akımı sınırlar (güvenlik) ve
AD620 girişlerini korur. AD620 yoksa INA128 kullanılabilir (G = 1 + 50 kΩ/RG, aynı RG ile G ≈ 51).

### [2] Yüksek geçiren + tampon

```
 TP1 ──||────┬──── (+) U1A ──┬── TP2
     1 µF    │     (−) ──────┘     (gerilim izleyici)
   (film)   8,2 kΩ
             │
            GND
```

**fc = 1 / (2π·R·C) = 1 / (2π · 8,2 kΩ · 1 µF) = 19,4 Hz**

Kondansatör kutupsuz (film/polyester) olmalı. Tampon, Twin-T'nin ihtiyaç duyduğu düşük kaynak empedansını sağlar.

### [3] Aktif Twin-T çentik filtre (50 Hz)

```
                  R = 31,6k          R = 31,6k
 TP2 ──┬─────────/\/\/─────┬─────/\/\/──────┬──────(+)U1B──┬──────── TP3
       │                   │                │      (−)─────┤
       │             2C = 200 nF            │              │
       │             (2×100 nF)             │            Ra 1,0k
       │                   │                │              │
       │                  Vf ◄──────────────┼───────┐      ●──(+)U1C──┬──► Vf
       │                   │                │       │      │   (−)────┤
       │          R/2 = 14,7k + 2k trim     │       │    Rb 9,1k      │
       │                   │                │       │      │          │
       └──────||───────────┴───────||───────┘       │     GND         │
          C = 100 nF            C = 100 nF          └─────────────────┘
```

Bağlantı özeti: Üst kol R–R, alt kol C–C. Üst kolun ortası **2C** ile, alt kolun ortası **R/2** ile
**Vf** düğümüne gider. Vf, çıkışın k katını süren bir gerilim izleyicidir (U1C). Pasif Twin-T'de
Vf = toprak olur ve Q = 0,25 kalır; bu da 20–100 Hz arasındaki kas sinyalini de yer.
Geri besleme ile çentik daraltılır:

- **f0 = 1 / (2π·R·C) = 1 / (2π · 31,6 kΩ · 100 nF) = 50,4 Hz**
- **k = Rb / (Ra + Rb) = 9,1 / 10,1 = 0,901**
- **Q = 1 / (4·(1 − k)) = 2,53** → −3 dB bant genişliği f0/Q ≈ 20 Hz (40–60 Hz)

Transfer fonksiyonu: H(s) = (s² + ω0²) / (s² + 4(1−k)·ω0·s + ω0²)

**Tolerans uyarısı:** Twin-T'nin derinliği elemanların birbirine ne kadar eşit olduğuna bağlıdır.
`tasarim_hesap.py` içindeki Monte Carlo analizi bunu gösterir:

![Twin-T tolerans](sekiller/centik_tolerans.png)

%5'lik kondansatörlerle 50 Hz bastırma 15–20 dB'e düşebilir. Bu yüzden:
1. Kondansatörleri multimetrenin kapasite kademesiyle ölçüp birbirine en yakın olanları seçin.
2. R/2 kolunu **14,7 kΩ + 2 kΩ trimpot** olarak kurun ve aşağıdaki ayar adımıyla çentiği derinleştirin.

### [4] Sallen-Key alçak geçiren (2. derece Butterworth)

```
                 R = 33k           R = 33k
 TP3 ───────────/\/\/─────┬───────/\/\/─────┬──────(+)U1D──┬──────── çıkış (→ [5])
                          │                 │      (−)──┐  │
                      C = 10 nF         C = 10 nF       │  │
                          │                 │           ├──┴─ Rf 5,9k (çıkış ile (−) arası)
                          │                GND          │
                          │                           Rg 10k
                          └──► çıkışa (geri besleme)    │
                                                       GND
```

Eşit elemanlı tasarım (R1 = R2, C1 = C2):

- **fc = 1 / (2π·R·C) = 1 / (2π · 33 kΩ · 10 nF) = 482 Hz**
- Butterworth için Q = 0,707 gerekir; eşit elemanlı Sallen-Key'de **Q = 1/(3 − K)** olduğundan
  **K = 3 − √2 = 1,586**. **K = 1 + Rf/Rg = 1 + 5,9/10 = 1,59** → Q = 0,709 ✓

### [5] Kazanç katı (evirmeyen)

**G = 1 + Rf/Rg = 1 + 120 kΩ / 10 kΩ = 13** — çıkış TP4 → osiloskop.

### Toplam

**G_toplam = 50,4 × 1,59 × 13 ≈ 1042 (60 dB)** → 1 mV'lik kas sinyali çıkışta ~1 V.

![Bode diyagramı](sekiller/bode.png)

| Frekans | 1 Hz | 10 Hz | 20 Hz | **50 Hz** | 100 Hz | 250 Hz | 480 Hz | 1 kHz | 2 kHz | 5 kHz |
|---|---|---|---|---|---|---|---|---|---|---|
| Zayıflatma (dB) | −25,8 | −6,8 | −3,0 | **−29,3** | −0,5 | −0,3 | −3,0 | −12,9 | −24,7 | −40,6 |

(Nominal değerlerle f0 = 50,37 Hz olduğundan tam 50 Hz'de bastırma ~29 dB; trimpot ayarıyla 35–40 dB'e çıkar.)

---

## 3. Malzeme listesi

| Adet | Malzeme | Not |
|---|---|---|
| 1 | AD620 (veya INA128) | Enstrümantasyon yükselteci |
| 1 | TL074 (veya TL084) dörtlü op-amp | U1A–U1D |
| 1 | TL072 (veya tek TL071) | Kazanç katı için 5. op-amp |
| 3 | Tek kullanımlık Ag/AgCl EKG elektrodu + çıtçıtlı kablo | Eczane/elektronikçi |
| 2 | 9 V pil + pil başlığı | ±9 V |
| — | Dirençler (%1 metal film) | 1,0k; 8,2k; 31,6k ×2; 14,7k; 1,0k; 9,1k; 33k ×2; 5,9k; 10k ×5; 120k |
| 1 | 2 kΩ çok turlu trimpot | Çentik ayarı |
| — | Kondansatörler (film/polyester) | 1 µF ×1; 100 nF ×4 (seçilmiş); 10 nF ×2 |
| 6 | 100 nF seramik | Her entegrenin besleme bacaklarına dekuplaj |
| — | Breadboard, kablolar | |

Tam değer bulunamazsa: 31,6k → 33k (f0 = 48 Hz, trimpot ile toparlanır); 5,9k → 5,6k (Q = 0,69, fark ihmal edilebilir).

---

## 4. Deney adımları

**A. Kat kat test (henüz vücuda bağlamadan, sinyal jeneratörüyle)**

1. ±9 V beslemeyi bağlayın, her entegrenin besleme bacaklarını ölçün.
2. Jeneratörden 1 Vpp sinüsü TP1 noktasına (AD620 çıkışını ayırarak) verin. 10, 20, 50, 100, 250, 480, 1000, 2000 Hz'de
   TP4'teki genliği ölçün; `kazanç(dB) = 20·log10(Vçıkış / Vgiriş) − 20·log10(20,7)` ile normalize edip yukarıdaki
   tabloyla karşılaştırın (20,7 = 1,59 × 13). Ölçülen noktaları Bode grafiğinin üzerine işleyin.
3. **Çentik ayarı:** jeneratörü 50,0 Hz'e ayarlayın, TP3'ü izleyerek trimpotu çıkış en küçük olana kadar çevirin.
4. AD620'yi kontrol için: jeneratörü 10 kΩ / 100 Ω bölücüyle ~10 mV'a indirip AD620 girişine verin; TP1'de ~0,5 V görmelisiniz.

**B. Elektrot yerleşimi (biseps)**

- Cildi alkolle silin. İki ölçüm elektrodunu biseps kasının ortasına, kas lifleri boyunca **2–3 cm arayla** yapıştırın.
- Referans elektrodunu kemikli bir bölgeye (dirsek) yapıştırın.
- Kabloları birbirine sarın/örün; kablo hareketi parazit üretir.

**C. Osiloskop ile kayıt**

| Ayar | CH1 = TP1 (ham) | CH2 = TP4 (filtreli) |
|---|---|---|
| Kuplaj | AC | AC |
| Volt/div | 50 mV | 500 mV |
| Zaman/div | 500 ms (ekranda 5 s) | |

1. Kas gevşekken ekranı izleyin: CH1'de belirgin bir 50 Hz dalgası, CH2'de neredeyse düz çizgi beklenir.
2. Kası 1–2 s kasın, 1–2 s gevşetin; birkaç kez tekrarlayın.
3. Osiloskopun **FFT (Math)** fonksiyonuyla her iki kanalın spektrumunu görün: 50 Hz tepesi CH2'de kaybolmalı.
4. Kaydı **CSV** olarak USB belleğe kaydedin (iki kanal aynı dosyada).
5. Analiz: `python olcum_analiz.py kayit.csv` → SNR değerleri ve grafikler.
   Sütunlar farklıysa `--zaman 0 --ham 1 --filtreli 2`, bölgeleri elle vermek için
   `--kasilma 1.2:2.5,4:5.3 --dinlenme 0:0.8,2.8:3.6` kullanın.

### SNR nasıl hesaplanıyor?

Gerçek ölçümde "temiz" sinyali bilmeyiz; bu yüzden kas gevşekken kaydedilen her şeyi gürültü kabul ederiz:

```
P_gürültü = P_dinlenme
P_sinyal  = P_kasılma − P_dinlenme
SNR (dB)  = 10 · log10( P_sinyal / P_gürültü )
```

Aynı formül ham (TP1) ve filtrelenmiş (TP4) kanala uygulanır; aradaki fark filtrenin SNR kazancıdır.
SNR bir oran olduğu için kanalların kazançlarının farklı olması sonucu etkilemez.

---

## 5. Benzetim sonuçları

`simulasyon.py`, gerçekçi bir yapay EMG sinyali (kasılma sırasında 0,5 mV RMS) üzerine projede
sayılan parazitleri ekler ve tasarlanan devreden geçirir:

| Parazit | Filtre öncesi (RMS) | Filtre sonrası (RMS) | Bastırma |
|---|---|---|---|
| Şebeke 50 Hz (temel) | 0,566 mV | 0,019 mV | **29,3 dB** |
| Şebeke harmonikleri (150/250 Hz) | 0,092 mV | 0,090 mV | 0,2 dB |
| Hareket / taban kayması (< 2 Hz) | 0,482 mV | 0,017 mV | 29,2 dB |
| Ani parazitler (1,5 ms darbe) | 0,046 mV | 0,039 mV | 1,5 dB |
| Yüksek frekans gürültü (geniş bant + 2,3 kHz) | 0,184 mV | 0,033 mV | 15,0 dB |

| SNR | Filtre öncesi | Filtre sonrası | İyileşme |
|---|---|---|---|
| Temiz sinyal bilinerek | −6,9 dB | 9,4 dB | **+16,3 dB** |
| Kasılma / dinlenme yöntemi (ölçümde kullanılacak) | −2,8 dB | 12,2 dB | **+15,0 dB** |

![Zaman düzlemi](sekiller/sim_zaman.png)

Alt paneldeki **kas kasılma grafiği**, projede beklenen "kası kastığımızda yükselen, gevşettiğimizde
düzleşen" eğridir: ham sinyalden çıkarılan zarf gürültü yüzünden kasılmayı ayırt edemezken
filtrelenmiş sinyalinki net biçimde yükselip iniyor.

![Yakın görünüm](sekiller/sim_yakin.png)

![Frekans düzlemi](sekiller/sim_frekans.png)

### Benzetimin gösterdiği sınırlar (raporda tartışılabilir)

- **Harmonikler geçiyor:** Çentik yalnızca 50 Hz'i bastırır; 150 Hz ve 250 Hz EMG bandının içinde olduğu için
  alçak geçiren de onlara dokunmaz. Gerekirse ikinci bir 150 Hz Twin-T eklenebilir.
- **Bant içi gürültü kalır:** 20–480 Hz arasındaki gürültü, sinyalle aynı frekanslarda olduğu için hiçbir filtre
  tarafından ayrılamaz. Filtrenin SNR kazancı bu yüzden sınırlıdır; asıl iyileştirme kaynağı düzgün elektrot teması
  ve kısa/örülü kablolardır.
- **Kısa darbeler:** 1–2 ms'lik ani parazitlerin enerjisi EMG bandına düştüğü için alçak geçiren onları ancak biraz yumuşatır.
- **Çentik tam 50 Hz'de değil:** Standart değerlerle f0 = 50,37 Hz; trimpotla ayar şart.

### Geliştirme fikirleri

- **Sağ bacak sürücüsü (DRL):** Referans elektrodunu ortak mod gerilimiyle ters sürerek 50 Hz'i kaynağında azaltır.
- **Analog zarf devresi:** Hassas doğrultucu + 5 Hz alçak geçiren ile "kas kasılma grafiği" doğrudan osiloskopta görünür.
- **4. derece alçak geçiren:** İki Sallen-Key art arda (Q = 0,541 ve 1,307) ile −80 dB/dekad.

---

## 6. Güvenlik

- Devreyi **yalnızca pille** besleyin. Elektrotlar vücuttayken devreyi **asla** prize bağlı bir adaptöre bağlamayın.
- Masaüstü osiloskopun toprak ucu şebeke toprağına bağlıdır; bu, referans elektrot üzerinden kişiyi toprağa bağlar.
  Normal çalışmada sorun yaratmaz, ancak bu yüzden elektrot hatlarındaki **10 kΩ seri dirençleri atlamayın**.
  Mümkünse pille çalışan el osiloskobu veya şarjı takılı olmayan dizüstü bilgisayara bağlı USB osiloskop kullanın.
- Elektrotların hepsini **aynı kola** yapıştırın; göğüs üzerinden (kolun birinden diğerine) bağlantı yapmayın.
- Kalp pili veya başka implantı olan kişilerde denemeyin.
