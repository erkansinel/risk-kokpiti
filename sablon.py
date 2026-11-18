"""Excel şablonunu üretir (boş veya örnek verili).

Kullanım:
    python sablon.py            -> sablonlar/ klasörüne boş şablon + örnek dosya yazar
"""
import io
import os
from datetime import date, datetime

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from sema import PARAMETRE_SAYFASI, PARAMETRELER, SAYFALAR, TALIMAT_SAYFASI

LACIVERT = "0F2744"
TURUNCU = "B45309"
GRI = "F1F5F9"
ZORUNLU_FILL = PatternFill("solid", fgColor=TURUNCU)
OPSIYONEL_FILL = PatternFill("solid", fgColor=LACIVERT)
BASLIK_FONT = Font(bold=True, color="FFFFFF", name="Calibri", size=11)
INCE = Side(style="thin", color="CBD5E1")
KENAR = Border(left=INCE, right=INCE, top=INCE, bottom=INCE)
SATIR_SAYISI = 500  # doğrulama kurallarının uygulanacağı satır sayısı

FORMAT = {
    "tutar": "#,##0.00",
    "tarih": "DD.MM.YYYY",
    "yuzde": "0",
    "gun": "0",
    "sayi": "0.####",
}


# ----------------------------------------------------------------------------
# Örnek veri (orta ölçekli bir mühendislik firması, analiz tarihi 18.11.2026)
# ----------------------------------------------------------------------------
def d(g, a, y=2026):
    return datetime(y, a, g)


ORNEK_PARAMETRE = {
    "Şirket Unvanı": "ABC Mühendislik ve Sanayi A.Ş.",
    "Analiz Tarihi": d(18, 11),
    "USD/TRY Kuru": 41.50,
    "EUR/TRY Kuru": 48.20,
    "Minimum Nakit Tamponu (TRY)": 500_000,
}

ORNEK = {
    "1_Banka_ve_Kasa": [
        ["Merkez Kasa", "", "TRY", 85_000, 0],
        ["Garanti TL Vadesiz", "Garanti BBVA", "TRY", 1_650_000, 0],
        ["Akbank TL Vadesiz", "Akbank", "TRY", 760_000, 250_000],
        ["İş Bankası USD", "İş Bankası", "USD", 18_500, 0],
        ["Yapı Kredi EUR", "Yapı Kredi", "EUR", 6_000, 0],
    ],
    "2_Musteri_Alacaklari": [
        ["Delta İnşaat A.Ş.", "İnşaat", "FTR-2026-1184", "TRY", 450_000, d(5, 11), "Havale/EFT", 85, 20, 15],
        ["Marmara Yapı Ltd.", "İnşaat", "ÇEK-445821", "TRY", 320_000, d(30, 11), "Çek", 80, 5, 10],
        ["Anka Enerji A.Ş.", "Enerji", "FTR-2026-1201", "TRY", 780_000, d(8, 12), "Havale/EFT", 90, 10, 10],
        ["Belediye Fen İşleri", "Kamu", "FTR-2026-1150", "TRY", 1_250_000, d(15, 12), "Havale/EFT", 75, 45, 30],
        ["Kuzey Otomotiv A.Ş.", "Otomotiv", "FTR-2026-1215", "TRY", 560_000, d(20, 12), "DBS", 95, 0, 3],
        ["Orion Makina Ltd.", "Sanayi", "SNT-0098", "TRY", 275_000, d(28, 12), "Senet", 70, 15, 20],
        ["Global Steel GmbH", "İhracat", "EXP-2026-071", "EUR", 42_000, d(10, 1, 2027), "Havale/EFT", 95, 5, 5],
        ["Ege Altyapı A.Ş.", "İnşaat", "FTR-2026-1230", "TRY", 830_000, d(15, 1, 2027), "Havale/EFT", 70, 30, 20],
        ["Atlas Trading LLC", "İhracat", "EXP-2026-075", "USD", 25_000, d(25, 1, 2027), "Havale/EFT", 90, 10, 10],
        ["Karadeniz Enerji", "Enerji", "FTR-2026-1244", "TRY", 410_000, d(5, 2, 2027), "Havale/EFT", 85, 10, 10],
    ],
    "3_Tedarikci_Borclari": [
        ["Ereğli Demir Çelik", "FTR-88412", "TRY", 650_000, d(25, 11), "Havale/EFT", 0, "Evet"],
        ["Bosch Rexroth", "INV-55120", "EUR", 14_500, d(2, 12), "Havale/EFT", 15, "Hayır"],
        ["Ankara Hırdavat", "ÇEK-V-1102", "TRY", 280_000, d(10, 12), "Verilen Çek", 0, "Hayır"],
        ["Öz Nakliyat", "FTR-3321", "TRY", 165_000, d(14, 11), "Havale/EFT", 20, "Hayır"],
        ["Siemens San.", "INV-77815", "USD", 21_000, d(20, 12), "Havale/EFT", 30, "Hayır"],
        ["Ege Boya", "FTR-9921", "TRY", 340_000, d(5, 1, 2027), "Havale/EFT", 30, "Hayır"],
        ["Ankara Hırdavat", "ÇEK-V-1108", "TRY", 300_000, d(15, 1, 2027), "Verilen Çek", 0, "Hayır"],
        ["Ereğli Demir Çelik", "FTR-88790", "TRY", 870_000, d(25, 1, 2027), "Havale/EFT", 0, "Evet"],
    ],
    "4_Sabit_Giderler": [
        ["Net Maaşlar", "Personel", "TRY", 720_000, 1, None, None, d(1, 1, 2027), 30],
        ["SGK Primleri", "SGK/Vergi", "TRY", 230_000, 26, None, None, d(1, 1, 2027), 30],
        ["Muhtasar Vergi", "SGK/Vergi", "TRY", 145_000, 26, None, None, None, 0],
        ["KDV Ödemesi", "SGK/Vergi", "TRY", 220_000, 28, None, None, None, 0],
        ["Fabrika Kirası", "Kira", "TRY", 165_000, 5, None, None, None, 0],
        ["Elektrik + Doğalgaz", "Enerji", "TRY", 95_000, 15, None, None, None, 0],
        ["Yazılım Lisansları", "Diğer", "USD", 2_400, 10, None, None, None, 0],
    ],
    "5_Finansman_Odemeleri": [
        ["Garanti BBVA", "Taksitli Kredi", "TRY", d(30, 11), 250_000, 62_000, "Hayır", 0],
        ["Garanti BBVA", "Taksitli Kredi", "TRY", d(30, 12), 250_000, 55_000, "Hayır", 0],
        ["Garanti BBVA", "Taksitli Kredi", "TRY", d(30, 1, 2027), 250_000, 48_000, "Hayır", 0],
        ["Akbank", "Spot Kredi", "TRY", d(22, 12), 1_000_000, 95_000, "Evet", 80],
        ["Halk Leasing", "Leasing", "EUR", d(10, 12), 4_800, 900, "Hayır", 0],
        ["Halk Leasing", "Leasing", "EUR", d(10, 1, 2027), 4_800, 850, "Hayır", 0],
        ["Halk Leasing", "Leasing", "EUR", d(10, 2, 2027), 4_800, 800, "Hayır", 0],
        ["Yapı Kredi", "Kredi Kartı", "TRY", d(3, 12), 85_000, 0, "Hayır", 0],
    ],
    "6_Kredi_Limitleri": [
        ["Garanti BBVA", "Rotatif Kredi", 1_500_000, 500_000, 48, 25, "Evet"],
        ["Akbank", "KMH/BCH", 400_000, 0, 62, 15, "Evet"],
        ["Ak Faktoring", "Faktoring", 800_000, 0, 52, 30, "Evet"],
    ],
    "7_Yonetim_Aksiyonlari": [
        ["Ortak cari hesabından fon", "Ortak Cari", 750_000, d(1, 12), 90, 0, 1, "Evet"],
        ["Atıl CNC tezgâhının satışı", "Varlık Satışı", 1_200_000, d(15, 1, 2027), 60, 20, 2, "Evet"],
        ["Bedelli sermaye artırımı", "Sermaye Artırımı", 2_000_000, d(1, 2, 2027), 70, 0, 3, "Evet"],
    ],
    "8_Satis_Tahmini": [
        [d(1, 12), "TRY", 1_900_000, 25],
        [d(1, 1, 2027), "TRY", 2_500_000, 25],
        [d(1, 1, 2027), "EUR", 15_000, 15],
        [d(1, 2, 2027), "TRY", 2_900_000, 30],
        [d(1, 2, 2027), "EUR", 20_000, 15],
    ],
    "9_Diger_Cikislar": [
        ["Geçici Vergi (3. Dönem)", "Vergi", "TRY", 380_000, d(17, 11)],
        ["Yeni Kaynak Robotu Peşinat", "Yatırım", "EUR", 25_000, d(15, 12)],
        ["Kurumlar Vergisi Taksidi", "Vergi", "TRY", 420_000, d(17, 2, 2027)],
    ],
}


# ----------------------------------------------------------------------------
def _baslik_yaz(ws, kolonlar):
    for j, k in enumerate(kolonlar, start=1):
        c = ws.cell(row=1, column=j, value=k.ad)
        c.font = BASLIK_FONT
        c.fill = ZORUNLU_FILL if k.zorunlu else OPSIYONEL_FILL
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = KENAR
        not_ = ("ZORUNLU. " if k.zorunlu else "Opsiyonel. ") + k.aciklama
        if k.secenekler:
            not_ += "\nSeçenekler: " + ", ".join(k.secenekler)
        if k.varsayilan not in (None, ""):
            not_ += f"\nBoş bırakılırsa: {k.varsayilan}"
        c.comment = Comment(not_, "Likidite Kokpiti", width=320, height=140)
        ws.column_dimensions[get_column_letter(j)].width = max(k.genislik, len(k.ad) * 0.95 + 3)
    ws.row_dimensions[1].height = 34
    ws.freeze_panes = "A2"


def _dogrulama_ekle(ws, kolonlar):
    son = SATIR_SAYISI + 1
    for j, k in enumerate(kolonlar, start=1):
        harf = get_column_letter(j)
        alan = f"{harf}2:{harf}{son}"
        dv = None
        if k.tip in ("liste", "evet_hayir"):
            dv = DataValidation(type="list", formula1='"' + ",".join(k.secenekler) + '"', allow_blank=True)
            dv.error = "Listeden bir değer seçin."
        elif k.tip == "yuzde":
            dv = DataValidation(type="decimal", operator="between", formula1="0", formula2="100", allow_blank=True)
            dv.error = "0 ile 100 arasında bir sayı girin (ör. 85)."
        elif k.tip == "tutar":
            dv = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0", allow_blank=True)
            dv.error = "Tutar 0 veya pozitif olmalı."
        elif k.tip == "tarih":
            dv = DataValidation(type="date", operator="greaterThan", formula1="36526", allow_blank=True)
            dv.error = "Geçerli bir tarih girin (GG.AA.YYYY)."
        elif k.tip == "gun":
            alt = "1" if k.ad == "Ödeme Günü" else "0"
            ust = "31" if k.ad == "Ödeme Günü" else "3650"
            dv = DataValidation(type="whole", operator="between", formula1=alt, formula2=ust, allow_blank=True)
            dv.error = f"{alt} ile {ust} arasında tam sayı girin."
        if dv is not None:
            dv.errorTitle = k.ad
            dv.showErrorMessage = True
            ws.add_data_validation(dv)
            dv.add(alan)
        if k.tip in FORMAT:
            for i in range(2, son + 1):
                ws.cell(row=i, column=j).number_format = FORMAT[k.tip]


def _talimat_sayfasi(wb):
    ws = wb.create_sheet(TALIMAT_SAYFASI, 0)
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 30
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 95
    r = 2
    ws.cell(row=r, column=2, value="Likidite Kokpiti — Veri Şablonu").font = Font(bold=True, size=18, color=LACIVERT)
    r += 1
    ws.cell(row=r, column=2, value="Monte Carlo nakit akışı stres testi için girdi dosyası").font = Font(
        italic=True, color="64748B")
    r += 2
    kurallar = [
        "1. Önce 0_Parametreler sayfasını doldurun. Tüm tarihler Analiz Tarihi'ne göre hesaplanır.",
        "2. Turuncu başlıklı kolonlar zorunludur; lacivert başlıklı kolonlar opsiyoneldir (boşsa varsayılan kullanılır).",
        "3. Başlık hücrelerinin üzerine gelince açıklama görünür. Başlık adlarını değiştirmeyin, sayfa adlarını değiştirmeyin.",
        "4. Tutarları kalemin kendi para biriminde yazın. Model USD/EUR kalemleri simüle edilen kurla TL'ye çevirir.",
        "5. Yüzdeleri 0–100 arası sayı olarak yazın (%85 → 85).",
        "6. Vadesi geçmiş kalemleri silmeyin: geçmiş vade tarihiyle bırakın; model bunları ilk günlere yerleştirir.",
        "7. Kullanmadığınız opsiyonel sayfaları boş bırakabilirsiniz; silmenize gerek yok.",
        "8. Aynı tutarı iki sayfada saymayın (ör. kesilmiş fatura hem 2. hem 8. sayfada olmamalı).",
    ]
    for k in kurallar:
        ws.cell(row=r, column=2, value=k).alignment = Alignment(wrap_text=True)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
        r += 1
    r += 1
    for j, t in enumerate(["Sayfa", "Durum", "İçerik"], start=2):
        c = ws.cell(row=r, column=j, value=t)
        c.font = BASLIK_FONT
        c.fill = OPSIYONEL_FILL
        c.border = KENAR
    r += 1
    satirlar = [(PARAMETRE_SAYFASI, True, "Şirket unvanı, analiz tarihi, döviz kurları, minimum nakit tamponu.")]
    satirlar += [(s.ad, s.zorunlu, s.aciklama) for s in SAYFALAR]
    for ad, zorunlu, aciklama in satirlar:
        ws.cell(row=r, column=2, value=ad).font = Font(bold=True)
        c = ws.cell(row=r, column=3, value="Zorunlu" if zorunlu else "Opsiyonel")
        c.font = Font(bold=True, color=TURUNCU if zorunlu else "475569")
        ws.cell(row=r, column=4, value=aciklama).alignment = Alignment(wrap_text=True, vertical="top")
        for j in (2, 3, 4):
            ws.cell(row=r, column=j).border = KENAR
            ws.cell(row=r, column=j).alignment = Alignment(wrap_text=True, vertical="top")
        r += 1


def _parametre_sayfasi(wb, ornek):
    ws = wb.create_sheet(PARAMETRE_SAYFASI)
    for j, t in enumerate(["Parametre", "Değer", "Açıklama"], start=1):
        c = ws.cell(row=1, column=j, value=t)
        c.font = BASLIK_FONT
        c.fill = OPSIYONEL_FILL
        c.border = KENAR
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 34
    ws.column_dimensions["C"].width = 90
    for i, (ad, tip, zorunlu, _vars, aciklama) in enumerate(PARAMETRELER, start=2):
        a = ws.cell(row=i, column=1, value=ad)
        a.font = Font(bold=True, color=TURUNCU if zorunlu else "0F172A")
        deger = ORNEK_PARAMETRE.get(ad) if ornek else (date.today() if tip == "tarih" else None)
        b = ws.cell(row=i, column=2, value=deger)
        b.fill = PatternFill("solid", fgColor="FFF7ED")
        if tip in FORMAT:
            b.number_format = FORMAT[tip]
        ws.cell(row=i, column=3, value=("ZORUNLU. " if zorunlu else "") + aciklama)
        for j in (1, 2, 3):
            ws.cell(row=i, column=j).border = KENAR
    ws.freeze_panes = "A2"


def sablon_olustur(ornek=False):
    """Şablonu bayt olarak döndürür."""
    wb = Workbook()
    wb.remove(wb.active)
    _talimat_sayfasi(wb)
    _parametre_sayfasi(wb, ornek)
    for s in SAYFALAR:
        ws = wb.create_sheet(s.ad)
        _baslik_yaz(ws, s.kolonlar)
        _dogrulama_ekle(ws, s.kolonlar)
        if ornek:
            for i, satir in enumerate(ORNEK.get(s.ad, []), start=2):
                assert len(satir) == len(s.kolonlar), (s.ad, satir)
                for j, v in enumerate(satir, start=1):
                    ws.cell(row=i, column=j, value=v)
        ws.sheet_properties.tabColor = TURUNCU if s.zorunlu else LACIVERT
    wb[PARAMETRE_SAYFASI].sheet_properties.tabColor = TURUNCU
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


if __name__ == "__main__":
    klasor = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sablonlar")
    os.makedirs(klasor, exist_ok=True)
    for ad, ornek in [("Likidite_Sablonu_BOS.xlsx", False), ("Likidite_Sablonu_ORNEK.xlsx", True)]:
        with open(os.path.join(klasor, ad), "wb") as f:
            f.write(sablon_olustur(ornek))
        print("yazıldı:", os.path.join(klasor, ad))
