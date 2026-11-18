# Likidite Kokpiti

Monte Carlo yöntemiyle nakit akışı stres testi. Şirketin Excel'deki verisinden binlerce senaryo üretir ve şu soruları cevaplar: nakit ne zaman tükenir, ne kadar ek kaynak gerekir, mevcut limitler ve yönetim aksiyonları yeterli mi?

## Kurulum ve çalıştırma
```bash
pip install -r requirements.txt
streamlit run app.py
```
Uygulama `C:\Programlarim\montecarlo\montecarlo_veri\Likidite_Sablonu.xlsx` dosyasını arar. Dosya yoksa örnek veriyle açılır. Ekrandan başka bir Excel de yüklenebilir.

## Dosyalar
| Dosya | Görev |
|---|---|
| `sema.py` | **Excel şablonunun tek tanımı.** Kolon eklemek/değiştirmek için yalnızca burası düzenlenir. |
| `sablon.py` | Boş şablonu ve örnek dosyayı üretir (`python sablon.py` → `sablonlar/`). |
| `veri.py` | Excel'i okur, temizler, satır satır kontrol eder; hataları raporlar. |
| `motor.py` | Simülasyon motoru (korelasyon, gecikme, kur, finansman sırası). |
| `app.py`, `stil.py` | Ekran ve görünüm. |
| `test_*.py` | Testler: `python -m pytest -q` |

## Excel şablonu
`0_Parametreler`, `1_Banka_ve_Kasa` ve `2_Musteri_Alacaklari` sayfaları zorunludur, diğerleri opsiyoneldir. Turuncu başlıklı kolonlar zorunlu, lacivert başlıklı kolonlar opsiyoneldir. Başlıkların üzerine gelince açıklama görünür. Ayrıntılar şablonun `Talimatlar` sayfasındadır.

## Modelin varsayımları
- **Müşteri tahsilatı:** Her fatura kendi ihtimaliyle tahsil edilir. Gecikme süresi, girilen ortalama ve belirsizlik değerine göre senaryodan senaryoya değişir. Kötü bir piyasa senaryosunda bütün müşteriler birlikte daha az ve daha geç öder (piyasa korelasyonu). Aynı segmentteki müşteriler ayrıca birlikte hareket eder. Kısmi tahsilat yoktur: fatura ya tamamen ödenir ya hiç ödenmez.
- **Yeni satış:** Aylık tahmin ayın günlerine eşit dağıtılır. Belirsizlik payı piyasa şokuyla birlikte hareket eder.
- **Tedarikçi:** Varsayılan olarak vadesinde ödenir. İyimser mod seçilirse maksimum erteleme süresinin sonunda ödenir. Kritik tedarikçi ve verilen çek hiçbir zaman ertelenmez.
- **Kredi ve leasing:** Ödeme planına göre işler. Yenilenebilir krediler belirtilen ihtimalle yenilenir; yenilenince sadece faiz ödenir. Kriz senaryolarında yenilenme ihtimali düşer.
- **Kur:** USD ve EUR, TL'deki ortak bir değer kaybı yolunu izler. Döviz hesapların TL karşılığı da bu yola göre değişir.
- **Kaynak kullanımı:** Bakiye tamponun altına düşünce sırasıyla kullanılır:
  1. Kredi limitleri, en düşük faizliden başlayarak. Kriz senaryolarında limit kesilebilir.
  2. Yönetim aksiyonları, öncelik sırasına göre, gerçekleşme ihtimaliyle ve tek seferde tamamı.

  Çekilen kredinin faizi günlük işler. Nakit fazlası oluşunca en pahalı kredi önce kapatılır.
- **Temerrüt:** Projeksiyon boyunca en az bir gün bakiyenin eksiye düşmesi.
- **Henüz modellenmeyenler:** Faktoringin alacak tutarıyla sınırlanması, döviz cinsinden limitler, kur şokunun piyasa kriziyle bağlantılı olması.
