# Maç Tahmin

Süper Lig ve Premier Lig için istatistiksel maç tahmini. GitHub Actions her gün kendiliğinden:

1. football-data.co.uk'tan güncel sonuçları, şutları ve bahis oranlarını indirir,
2. (anahtar tanımlıysa) API-Football'dan günün oranlarını çekip arşivler,
3. modeli yeniden eğitip önümüzdeki maçların tahminlerini üretir,
4. eski tahminleri gerçek sonuçlarla karşılaştırıp canlı performans kaydını günceller,
5. her şeyi bu depoya kaydeder.

Bilgisayarının açık olmasına gerek yoktur. İstatistiksel tahmindir, bahis tavsiyesi değildir.

## Nereye bakmalı?

| Dosya | İçerik |
|---|---|
| `raporlar/bu_hafta.md` | Önümüzdeki maçların tahmin tablosu |
| `raporlar/performans.md` | Geçmiş tahminlerin gerçek sonuçlara göre başarısı |
| `tahminler/guncel.csv` | En son tahminler (uygulama buradan okuyabilir) |
| `tahminler/arsiv.csv` | Yapılmış bütün tahminlerin geçmişi |

## Klasörler

```
model/poisson_model.py       Model (Poisson + Dixon-Coles, şut verisi, lig ayarları, düzeltmeler)
scripts/veri_indir.py        football-data.co.uk indirme
scripts/api_football_veri.py API-Football oran arşivi (isteğe bağlı)
scripts/tahmin.py            Tahmin üretme
scripts/degerlendir.py       Canlı performans kaydı
data/                        Sezon dosyaları (otomatik güncellenir)
.github/workflows/gunluk.yml Günlük çalışma planı
```

## Kurulum (bir kez)

### 1. Depoyu oluştur
1. github.com'da oturum aç → sağ üstte **+** → **New repository**.
2. Ad: `mac-tahmin`. **Public** önerilir (GitHub Actions süresiz ücretsiz olur; API anahtarı yine gizli kalır).
   Private da olur (ayda 2.000 dakika ücretsiz; bu iş günde birkaç dakika sürer).
3. "Add a README file" kutusunu **işaretleme** → **Create repository**.

### 2. Dosyaları yükle
1. Yeni depoda **uploading an existing file** bağlantısına tıkla.
2. Zip'ten çıkardığın `mac-tahmin` klasörünün **içindekileri** (model, scripts, data, ... klasörleri ve dosyalar)
   sürükleyip bırak → **Commit changes**.
3. **Önemli:** `.github` klasörü noktayla başladığı için Windows ve macOS'ta gizli olabilir ve yüklenmeyebilir.
   Yüklendiğinden emin değilsen: depoda **Add file → Create new file** → dosya adına
   `.github/workflows/gunluk.yml` yaz → zip'teki aynı dosyanın içeriğini yapıştır → **Commit changes**.

### 3. Actions'a yazma izni ver
**Settings → Actions → General → Workflow permissions → Read and write permissions → Save.**
(Otomasyonun sonuçları depoya kaydedebilmesi için gerekli.)

### 4. API-Football anahtarını ekle (isteğe bağlı ama önerilir)
1. dashboard.api-football.com/register → ücretsiz hesap → **Account → My Access** → anahtarı kopyala.
2. Depoda **Settings → Secrets and variables → Actions → New repository secret**.
3. Name: `APIFOOTBALL_KEY`, Secret: anahtar → **Add secret**.

Anahtar hiçbir dosyaya yazılmaz; depo herkese açık olsa bile kimse göremez.
Anahtar eklenmezse o adım atlanır, geri kalan her şey çalışır.

### 5. İlk çalıştırma
**Actions** sekmesi → soldan **Günlük veri ve tahmin** → **Run workflow**.
Birkaç dakika sonra yeşil tik görünür ve `raporlar/bu_hafta.md` dolar.
Kırmızı çarpı çıkarsa çalışmaya tıklayıp hangi adımın hata verdiğine bak.

## Bilinmesi gerekenler
- Otomasyon her gün **08:17** ve **17:43** (Türkiye saati) civarında çalışır; GitHub zamanlanmış işleri
  yoğunlukta birkaç dakika–saat geciktirebilir.
- `fixtures.csv` maçları genelde birkaç gün önceden listeler; hafta başında tablo boş olabilir.
- Depoda 60 gün hiç hareket olmazsa GitHub zamanlanmış işi durdurabilir; Actions sekmesinde yeniden etkinleştirilir.
- Bir takım adı geçmiş verideki yazımdan farklıysa raporda **Uyarı** satırı çıkar.
