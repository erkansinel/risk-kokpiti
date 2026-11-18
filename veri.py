"""Excel şablonunu okur, şemaya göre temizler ve kontrol eder.

Hatalı satırlar atlanır ve kullanıcıya hangi sayfa / satırda ne sorun olduğu raporlanır.
"""
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from sema import PARA_BIRIMLERI, PARAMETRE_SAYFASI, PARAMETRELER, SAYFALAR

EVET = {"evet", "e", "yes", "y", "1", "true", "doğru", "x"}


@dataclass
class Bulgu:
    seviye: str   # "hata" | "uyari" | "bilgi"
    sayfa: str
    mesaj: str


@dataclass
class Veri:
    parametre: dict
    tablolar: dict              # sayfa adı -> temiz DataFrame
    bulgular: list = field(default_factory=list)

    @property
    def analiz_tarihi(self) -> date:
        return self.parametre["Analiz Tarihi"]

    def kur(self, para):
        return 1.0 if para == "TRY" else self.parametre.get(f"{para}/TRY Kuru")

    @property
    def hatali(self):
        return any(b.seviye == "hata" for b in self.bulgular)


class SablonHatasi(Exception):
    pass


def _bos(v):
    if v is None:
        return True
    if isinstance(v, str):
        return not v.strip()
    try:
        return bool(pd.isna(v))
    except (TypeError, ValueError):
        return False


def _tarih(v):
    if _bos(v):
        return None
    try:
        t = pd.to_datetime(v, dayfirst=True)
        return None if pd.isna(t) else t.date()
    except Exception:
        return "HATA"


def _sayi(v):
    if _bos(v):
        return None
    if isinstance(v, str):  # "1.250.000,50" veya "1,250,000.50"
        s = v.strip().replace("%", "").replace("₺", "").replace(" ", "")
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
        elif "," in s:
            s = s.replace(",", ".")
        v = s
    try:
        f = float(v)
        return None if np.isnan(f) else f
    except Exception:
        return "HATA"


def _parametreleri_oku(xls, bulgular):
    if PARAMETRE_SAYFASI not in xls.sheet_names:
        raise SablonHatasi(f"'{PARAMETRE_SAYFASI}' sayfası bulunamadı.")
    df = pd.read_excel(xls, sheet_name=PARAMETRE_SAYFASI, header=0, dtype=object)
    ham = {str(r.iloc[0]).strip(): r.iloc[1] for _, r in df.iterrows() if pd.notna(r.iloc[0])}
    p = {}
    for ad, tip, zorunlu, vars_, _ in PARAMETRELER:
        v = ham.get(ad)
        if tip == "tarih":
            v = _tarih(v)
        elif tip in ("sayi", "tutar"):
            v = _sayi(v)
        elif _bos(v):
            v = None
        else:
            v = str(v).strip()
        if v == "HATA":
            bulgular.append(Bulgu("hata", PARAMETRE_SAYFASI, f"'{ad}' değeri okunamadı."))
            v = None
        if v in (None, ""):
            if zorunlu:
                if ad == "Analiz Tarihi":
                    v = date.today()
                    bulgular.append(Bulgu("uyari", PARAMETRE_SAYFASI,
                                          "Analiz Tarihi boş; bugünün tarihi kullanıldı."))
                elif ad == "Şirket Unvanı":
                    v = "İsimsiz Şirket"
                else:
                    bulgular.append(Bulgu("hata", PARAMETRE_SAYFASI, f"'{ad}' zorunludur."))
            else:
                v = vars_
        p[ad] = v
    return p


def _sayfayi_oku(xls, sayfa, bulgular):
    if sayfa.ad not in xls.sheet_names:
        if sayfa.zorunlu:
            raise SablonHatasi(f"Zorunlu '{sayfa.ad}' sayfası bulunamadı.")
        bulgular.append(Bulgu("bilgi", sayfa.ad, "Sayfa yok; bu kalem hesaba katılmadı."))
        return pd.DataFrame(columns=[k.ad for k in sayfa.kolonlar])

    df = pd.read_excel(xls, sheet_name=sayfa.ad, header=0, dtype=object)
    df.columns = [str(c).strip() for c in df.columns]

    eksik_zorunlu = [k.ad for k in sayfa.kolonlar if k.zorunlu and k.ad not in df.columns]
    if eksik_zorunlu:
        raise SablonHatasi(f"'{sayfa.ad}' sayfasında zorunlu kolon(lar) yok: {', '.join(eksik_zorunlu)}. "
                           "Güncel şablonu kullandığınızdan emin olun.")
    for k in sayfa.kolonlar:
        if k.ad not in df.columns:
            df[k.ad] = None
            bulgular.append(Bulgu("bilgi", sayfa.ad, f"'{k.ad}' kolonu yok; varsayılan ({k.varsayilan}) kullanıldı."))

    temiz, atlanan = [], 0
    for i, r in df.iterrows():
        excel_satir = i + 2
        if all(_bos(r.get(k.ad)) for k in sayfa.kolonlar):
            continue  # tamamen boş satır
        satir, sorun = {}, None
        for k in sayfa.kolonlar:
            v = r.get(k.ad)
            if _bos(v):
                if k.zorunlu:
                    sorun = f"{excel_satir}. satır: '{k.ad}' boş"
                    break
                v = k.varsayilan
            elif k.tip == "tarih":
                v = _tarih(v)
                if v == "HATA":
                    sorun = f"{excel_satir}. satır: '{k.ad}' tarih olarak okunamadı"
                    break
            elif k.tip in ("tutar", "yuzde", "gun", "sayi"):
                v = _sayi(v)
                if v == "HATA" or v is None:
                    sorun = f"{excel_satir}. satır: '{k.ad}' sayı olarak okunamadı"
                    break
                if k.tip in ("tutar", "gun") and v < 0:
                    sorun = f"{excel_satir}. satır: '{k.ad}' negatif olamaz"
                    break
            elif k.tip == "evet_hayir":
                v = "Evet" if str(v).strip().lower() in EVET else "Hayır"
            elif k.tip == "liste":
                v = str(v).strip()
                eslesen = next((s for s in k.secenekler if s.lower() == v.lower()), None)
                if eslesen is None:
                    if k.zorunlu and k.ad == "Para Birimi":
                        sorun = f"{excel_satir}. satır: para birimi '{v}' desteklenmiyor ({', '.join(PARA_BIRIMLERI)})"
                        break
                    bulgular.append(Bulgu("uyari", sayfa.ad,
                                          f"{excel_satir}. satır: '{k.ad}' = '{v}' listede yok; '{k.varsayilan}' kabul edildi."))
                    eslesen = k.varsayilan
                v = eslesen
            else:
                v = str(v).strip()
            satir[k.ad] = v
        if sorun:
            atlanan += 1
            bulgular.append(Bulgu("hata", sayfa.ad, sorun + " — satır hesaba katılmadı."))
            continue
        satir["_satir"] = excel_satir
        temiz.append(satir)

    out = pd.DataFrame(temiz, columns=[k.ad for k in sayfa.kolonlar] + ["_satir"])

    # Yüzde kolonları: 0 < değer <= 1 olanlar Excel % biçimiyle girilmiş kabul edilir (0,85 → %85)
    for k in sayfa.kolonlar:
        if k.tip == "yuzde" and len(out):
            s = pd.to_numeric(out[k.ad], errors="coerce")
            kesir = (s > 0) & (s <= 1)
            if kesir.any():
                out.loc[kesir, k.ad] = s[kesir] * 100
                satirlar = ", ".join(str(x) for x in out.loc[kesir, "_satir"].head(5))
                bulgular.append(Bulgu("uyari", sayfa.ad,
                                      f"'{k.ad}' {kesir.sum()} satırda 0–1 arasında (satır {satirlar}); "
                                      "Excel yüzde biçimi kabul edilip 100 ile çarpıldı (0,85 → 85)."))
            if (s > 100).any():
                bulgular.append(Bulgu("uyari", sayfa.ad, f"'{k.ad}' 100'den büyük değer içeriyor; 100 kabul edildi."))
                out[k.ad] = pd.to_numeric(out[k.ad]).clip(upper=100)
    return out


def _capraz_kontroller(v: Veri):
    b, bas = v.bulgular, v.analiz_tarihi
    # Kur kontrolü
    for ad, df in v.tablolar.items():
        if "Para Birimi" in df.columns:
            for para in set(df["Para Birimi"]) - {"TRY"}:
                if not v.kur(para):
                    b.append(Bulgu("hata", ad, f"{para} kalem var ama 0_Parametreler'de {para}/TRY Kuru boş."))
    # Vadesi geçmiş kalemler
    for ad, kolon, metin in [("2_Musteri_Alacaklari", "Vade Tarihi", "vadesi geçmiş alacak"),
                             ("3_Tedarikci_Borclari", "Vade Tarihi", "vadesi geçmiş borç"),
                             ("5_Finansman_Odemeleri", "Ödeme Tarihi", "vadesi geçmiş kredi ödemesi")]:
        df = v.tablolar[ad]
        if len(df):
            gecmis = df[df[kolon] < bas]
            if len(gecmis):
                b.append(Bulgu("bilgi", ad, f"{len(gecmis)} adet {metin} var; ilk günlere yerleştirildi."))
    lim = v.tablolar["6_Kredi_Limitleri"]
    if len(lim):
        fazla = lim[lim["Kullanılan (TRY)"] > lim["Toplam Limit (TRY)"]]
        for _, r in fazla.iterrows():
            b.append(Bulgu("uyari", "6_Kredi_Limitleri",
                           f"{r['_satir']}. satır: kullanılan tutar limitten büyük; kullanılabilir limit 0 kabul edildi."))
    if not len(v.tablolar["8_Satis_Tahmini"]) and len(v.tablolar["4_Sabit_Giderler"]):
        b.append(Bulgu("uyari", "8_Satis_Tahmini",
                       "Yeni satış tahmini girilmemiş. Giderler her ay tekrar ederken yeni tahsilat olmadığı için "
                       "uzun projeksiyonlar olduğundan kötü görünür."))


def oku(kaynak) -> Veri:
    """kaynak: dosya yolu veya bayt. SablonHatasi fırlatabilir."""
    import io
    if isinstance(kaynak, (bytes, bytearray)):
        kaynak = io.BytesIO(kaynak)
    try:
        xls = pd.ExcelFile(kaynak)
    except Exception as e:
        raise SablonHatasi(f"Excel dosyası açılamadı: {e}")

    eski = {"1_Banka_ve_Kasa", "2_Musteri_Alacaklari"} <= set(xls.sheet_names) and PARAMETRE_SAYFASI not in xls.sheet_names
    if eski:
        raise SablonHatasi("Bu dosya eski şablon biçiminde (0_Parametreler sayfası yok). "
                           "Lütfen yeni şablonu indirip verileri ona aktarın.")
    bulgular = []
    parametre = _parametreleri_oku(xls, bulgular)
    tablolar = {s.ad: _sayfayi_oku(xls, s, bulgular) for s in SAYFALAR}
    v = Veri(parametre, tablolar, bulgular)
    _capraz_kontroller(v)
    if not len(tablolar["1_Banka_ve_Kasa"]):
        bulgular.append(Bulgu("uyari", "1_Banka_ve_Kasa", "Hiç banka/kasa hesabı yok; başlangıç nakdi 0 kabul edildi."))
    return v
