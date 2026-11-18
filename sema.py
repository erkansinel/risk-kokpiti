"""Excel şablonunun tek doğruluk kaynağı.

Şablon üretici (sablon.py), veri okuyucu (veri.py) ve uygulama aynı tanımı kullanır.
Bir kolon eklemek/değiştirmek için yalnızca burayı düzenleyin.
"""
from dataclasses import dataclass, field

PARA_BIRIMLERI = ("TRY", "USD", "EUR")
EVET_HAYIR = ("Evet", "Hayır")


@dataclass
class Kolon:
    ad: str
    tip: str            # metin | tutar | tarih | yuzde | gun | sayi | evet_hayir | liste
    zorunlu: bool
    aciklama: str
    secenekler: tuple = ()
    varsayilan: object = None
    genislik: int = 16


@dataclass
class Sayfa:
    ad: str
    baslik: str
    zorunlu: bool
    aciklama: str
    kolonlar: list = field(default_factory=list)

    def kolon(self, ad):
        return next(k for k in self.kolonlar if k.ad == ad)


# Parametreler sayfası anahtar–değer biçimindedir
PARAMETRELER = [
    # (ad, tip, zorunlu, varsayılan, açıklama)
    ("Şirket Unvanı", "metin", True, "", "Raporlarda görünecek unvan."),
    ("Analiz Tarihi", "tarih", True, None,
     "Bakiyelerin alındığı gün. Tüm tarihler bu güne göre hesaplanır (0. gün)."),
    ("USD/TRY Kuru", "sayi", False, None, "Analiz tarihindeki kur. USD kalem varsa zorunlu."),
    ("EUR/TRY Kuru", "sayi", False, None, "Analiz tarihindeki kur. EUR kalem varsa zorunlu."),
    ("Minimum Nakit Tamponu (TRY)", "tutar", False, 0,
     "Şirketin altına düşmek istemediği nakit seviyesi. Kaynaklar bu seviyeyi korumak için kullanılır."),
]

SAYFALAR = [
    Sayfa("1_Banka_ve_Kasa", "Banka ve Kasa", True,
          "Analiz tarihindeki tüm kasa ve banka hesapları. Her hesap bir satır.",
          [
              Kolon("Hesap", "metin", True, "Hesap adı (ör. Garanti TL Vadesiz).", genislik=28),
              Kolon("Banka", "metin", False, "Banka adı.", genislik=18),
              Kolon("Para Birimi", "liste", True, "TRY, USD veya EUR.", PARA_BIRIMLERI, "TRY", 12),
              Kolon("Bakiye", "tutar", True, "Hesap bakiyesi (hesabın kendi para biriminde)."),
              Kolon("Bloke Tutar", "tutar", False,
                    "Kullanılamayan kısım (teminat, haciz, vadeli hesap vb.).", varsayilan=0),
          ]),
    Sayfa("2_Musteri_Alacaklari", "Müşteri Alacakları", True,
          "Kesilmiş, henüz tahsil edilmemiş faturalar ve alınan çek/senetler. Her belge bir satır.",
          [
              Kolon("Müşteri", "metin", True, "Müşteri unvanı.", genislik=28),
              Kolon("Segment", "metin", False,
                    "Sektör veya müşteri grubu (ör. İnşaat, Kamu, İhracat). Aynı segmentteki müşteriler "
                    "krizde birlikte gecikir.", varsayilan="Genel"),
              Kolon("Belge No", "metin", False, "Fatura / çek / senet numarası."),
              Kolon("Para Birimi", "liste", True, "TRY, USD veya EUR.", PARA_BIRIMLERI, "TRY", 12),
              Kolon("Tutar", "tutar", True, "Tahsil edilecek tutar."),
              Kolon("Vade Tarihi", "tarih", True, "Sözleşmeye göre tahsilat tarihi. Geçmiş tarih olabilir."),
              Kolon("Ödeme Aracı", "liste", False, "Tahsilatın şekli.",
                    ("Havale/EFT", "Çek", "Senet", "DBS", "Kredi Kartı", "Diğer"), "Havale/EFT"),
              Kolon("Tahsilat İhtimali (%)", "yuzde", True,
                    "Bu tutarın projeksiyon süresinde tahsil edilme ihtimali (0–100)."),
              Kolon("Ortalama Gecikme (Gün)", "gun", False,
                    "Müşterinin vadeden sonra ortalama kaç gün geç ödediği.", varsayilan=0),
              Kolon("Gecikme Belirsizliği (± Gün)", "gun", False,
                    "Gecikmenin ne kadar oynayabileceği. Örn. 15 → çoğu senaryoda ±15 gün sapma.",
                    varsayilan=0),
          ]),
    Sayfa("3_Tedarikci_Borclari", "Tedarikçi Borçları", False,
          "Ödenmemiş tedarikçi faturaları ve verilen çek/senetler. Her belge bir satır.",
          [
              Kolon("Tedarikçi", "metin", True, "Tedarikçi unvanı.", genislik=28),
              Kolon("Belge No", "metin", False, "Fatura / çek / senet numarası."),
              Kolon("Para Birimi", "liste", True, "TRY, USD veya EUR.", PARA_BIRIMLERI, "TRY", 12),
              Kolon("Tutar", "tutar", True, "Ödenecek tutar."),
              Kolon("Vade Tarihi", "tarih", True, "Sözleşmeye göre ödeme tarihi. Geçmiş tarih olabilir."),
              Kolon("Ödeme Aracı", "liste", False, "Verilen çek ertelenemez kabul edilir.",
                    ("Havale/EFT", "Verilen Çek", "Senet", "DBS", "Kredi Kartı", "Diğer"), "Havale/EFT"),
              Kolon("Maks. Erteleme (Gün)", "gun", False,
                    "Tedarikçinin vadeden sonra en fazla kaç gün bekleyebileceği.", varsayilan=0),
              Kolon("Kritik Tedarikçi", "evet_hayir", False,
                    "Evet ise ödeme hiçbir senaryoda ertelenmez (ör. hammadde, enerji).",
                    EVET_HAYIR, "Hayır", 14),
          ]),
    Sayfa("4_Sabit_Giderler", "Sabit Giderler", False,
          "Her ay tekrarlanan giderler: maaş, SGK, kira, enerji vb.",
          [
              Kolon("Gider Kalemi", "metin", True, "Gider adı.", genislik=26),
              Kolon("Kategori", "liste", False, "Raporlamada gruplama için.",
                    ("Personel", "SGK/Vergi", "Kira", "Enerji", "Sigorta", "Diğer"), "Diğer"),
              Kolon("Para Birimi", "liste", True, "TRY, USD veya EUR.", PARA_BIRIMLERI, "TRY", 12),
              Kolon("Aylık Tutar", "tutar", True, "Bir aylık ödeme tutarı."),
              Kolon("Ödeme Günü", "gun", True, "Ayın kaçıncı günü ödendiği (1–31). 31 → ayın son günü."),
              Kolon("Başlangıç Tarihi", "tarih", False, "Boşsa analiz tarihinden itibaren geçerli."),
              Kolon("Bitiş Tarihi", "tarih", False, "Boşsa süresiz."),
              Kolon("Artış Tarihi", "tarih", False, "Zam/artışın geçerli olacağı tarih (ör. 01.01.2027)."),
              Kolon("Artış Oranı (%)", "yuzde", False, "Artış tarihinden sonra uygulanacak oran.", varsayilan=0),
          ]),
    Sayfa("5_Finansman_Odemeleri", "Kredi ve Leasing Ödemeleri", False,
          "Mevcut kredi, leasing ve kredi kartı geri ödemeleri. Banka ödeme planı satır satır kopyalanabilir.",
          [
              Kolon("Kurum", "metin", True, "Banka / leasing şirketi.", genislik=22),
              Kolon("Tür", "liste", True, "Finansman türü.",
                    ("Taksitli Kredi", "Spot Kredi", "Rotatif Kredi", "Leasing", "Kredi Kartı", "Diğer"),
                    "Taksitli Kredi"),
              Kolon("Para Birimi", "liste", True, "TRY, USD veya EUR.", PARA_BIRIMLERI, "TRY", 12),
              Kolon("Ödeme Tarihi", "tarih", True, "Taksit / vade tarihi."),
              Kolon("Anapara", "tutar", True, "Bu ödemedeki anapara."),
              Kolon("Faiz", "tutar", False, "Bu ödemedeki faiz + BSMV/KKDF.", varsayilan=0),
              Kolon("Yenilenebilir", "evet_hayir", False,
                    "Evet ise vadede anapara yeniden çevrilebilir (roll-over); yalnızca faiz ödenir.",
                    EVET_HAYIR, "Hayır", 14),
              Kolon("Yenilenme İhtimali (%)", "yuzde", False,
                    "Bankanın krediyi yenileme ihtimali. Kriz senaryolarında daha düşük gerçekleşir.",
                    varsayilan=0),
          ]),
    Sayfa("6_Kredi_Limitleri", "Kullanılabilir Kredi Limitleri", False,
          "Bankaların tanıdığı ama henüz tamamı kullanılmamış nakdi limitler. Tutarlar TRY.",
          [
              Kolon("Banka", "metin", True, "Banka / faktoring şirketi.", genislik=22),
              Kolon("Limit Türü", "liste", True, "Limitin türü.",
                    ("Rotatif Kredi", "KMH/BCH", "Spot Kredi", "Faktoring", "Çek İskonto", "Diğer"),
                    "Rotatif Kredi"),
              Kolon("Toplam Limit (TRY)", "tutar", True, "Tahsis edilen nakdi limit."),
              Kolon("Kullanılan (TRY)", "tutar", False,
                    "Bugün kullanılmış kısım. Geri ödemesi 5. sayfada olmalıdır.", varsayilan=0),
              Kolon("Yıllık Faiz (%)", "yuzde", False, "Çekilen tutara uygulanacak yıllık maliyet.",
                    varsayilan=0),
              Kolon("Kesilme İhtimali (%)", "yuzde", False,
                    "Kriz döneminde bankanın limiti dondurma ihtimali.", varsayilan=0),
              Kolon("Kullanılsın", "evet_hayir", False, "Hayır ise model bu limiti kullanmaz.",
                    EVET_HAYIR, "Evet", 12),
          ]),
    Sayfa("7_Yonetim_Aksiyonlari", "Yönetim Aksiyonları", False,
          "Gerekirse başvurulabilecek ek kaynaklar: ortak desteği, sermaye artırımı, varlık satışı vb.",
          [
              Kolon("Aksiyon", "metin", True, "Açıklama (ör. Ortak cari hesabından fon).", genislik=30),
              Kolon("Tür", "liste", True, "Aksiyonun türü.",
                    ("Ortak Cari", "Sermaye Artırımı", "Varlık Satışı", "Gider Kısıntısı", "Diğer"),
                    "Ortak Cari"),
              Kolon("Tutar (TRY)", "tutar", True,
                    "Brüt tutar. Gider kısıntısı için projeksiyon boyunca toplam tasarruf."),
              Kolon("En Erken Tarih", "tarih", True, "Bu kaynağın en erken hazır olabileceği tarih."),
              Kolon("Gerçekleşme İhtimali (%)", "yuzde", False, "Aksiyonun gerçekten yapılabilme ihtimali.",
                    varsayilan=100),
              Kolon("Kayıp / İskonto (%)", "yuzde", False,
                    "Acil satış iskontosu, masraf vb. Net giriş = Tutar × (1 − oran).", varsayilan=0),
              Kolon("Öncelik", "sayi", False, "Küçük numara önce kullanılır.", varsayilan=99, genislik=10),
              Kolon("Kullanılsın", "evet_hayir", False, "Hayır ise model bu aksiyonu kullanmaz.",
                    EVET_HAYIR, "Evet", 12),
          ]),
    Sayfa("8_Satis_Tahmini", "Yeni Satış Tahsilatı Tahmini", False,
          "Henüz faturası kesilmemiş satışlardan beklenen AYLIK tahsilat. 2. sayfadaki faturaları "
          "burada tekrar saymayın. İçinde bulunulan ay için yalnızca analiz tarihinden sonrasını yazın.",
          [
              Kolon("Ay", "tarih", True, "Ayın herhangi bir günü (ör. 01.12.2026)."),
              Kolon("Para Birimi", "liste", True, "TRY, USD veya EUR.", PARA_BIRIMLERI, "TRY", 12),
              Kolon("Beklenen Tahsilat", "tutar", True, "O ay içinde beklenen toplam tahsilat."),
              Kolon("Belirsizlik (± %)", "yuzde", False,
                    "Tahminin ne kadar sapabileceği. 20 → çoğu senaryoda ±%20.", varsayilan=20),
          ]),
    Sayfa("9_Diger_Cikislar", "Diğer Planlı Çıkışlar", False,
          "Tek seferlik çıkışlar: vergi, yatırım harcaması, temettü vb.",
          [
              Kolon("Açıklama", "metin", True, "Çıkışın adı.", genislik=28),
              Kolon("Kategori", "liste", False, "Raporlamada gruplama için.",
                    ("Vergi", "Yatırım", "Temettü", "Diğer"), "Diğer"),
              Kolon("Para Birimi", "liste", True, "TRY, USD veya EUR.", PARA_BIRIMLERI, "TRY", 12),
              Kolon("Tutar", "tutar", True, "Ödenecek tutar."),
              Kolon("Tarih", "tarih", True, "Ödeme tarihi."),
          ]),
]

SAYFA = {s.ad: s for s in SAYFALAR}
PARAMETRE_SAYFASI = "0_Parametreler"
TALIMAT_SAYFASI = "Talimatlar"
