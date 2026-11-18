"""Veri okuyucu ve arayüz testleri:  python -m pytest -q"""
import io

from openpyxl import load_workbook
from streamlit.testing.v1 import AppTest

import veri as V
from sablon import sablon_olustur


def hatali_dosya():
    wb = load_workbook(io.BytesIO(sablon_olustur(True)))
    ws = wb["2_Musteri_Alacaklari"]
    satirlar = [
        ["Hatalı Müşteri", "İnşaat", "X1", "TRY", "yüz bin", "15.12.2026", "Havale/EFT", 80, 0, 0],
        ["GBP Müşteri", "İhracat", "X2", "GBP", 1000, "15.12.2026", "Havale/EFT", 80, 0, 0],
        ["Metin Tutar", "Kamu", "X3", "try", "1.250.000,50", "20.12.2026", "havale/eft", 0.9, None, None],
    ]
    for i, satir in enumerate(satirlar, start=12):
        for j, deger in enumerate(satir, start=1):
            ws.cell(row=i, column=j, value=deger)
    wb["0_Parametreler"]["B4"] = None  # USD kuru silindi
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_ornek_dosya_temiz_okunur():
    v = V.oku(sablon_olustur(True))
    assert not v.hatali
    assert len(v.tablolar["2_Musteri_Alacaklari"]) == 10


def test_bos_sablon_okunur():
    v = V.oku(sablon_olustur(False))
    assert not v.hatali
    assert all(len(df) == 0 for df in v.tablolar.values())


def test_hatali_satirlar_raporlanir_ve_atlanir():
    v = V.oku(hatali_dosya())
    mesajlar = " ".join(b.mesaj for b in v.bulgular)
    assert "12. satır: 'Tutar' sayı olarak okunamadı" in mesajlar
    assert "13. satır: para birimi 'GBP' desteklenmiyor" in mesajlar
    assert "USD/TRY Kuru boş" in mesajlar
    al = v.tablolar["2_Musteri_Alacaklari"]
    son = al.iloc[-1]
    assert son["Müşteri"] == "Metin Tutar" and son["Tutar"] == 1250000.5
    assert son["Para Birimi"] == "TRY" and son["Ödeme Aracı"] == "Havale/EFT"
    assert son["Tahsilat İhtimali (%)"] == 90          # 0,9 → %90


def test_eski_sablon_taninir():
    from openpyxl import Workbook
    wb = Workbook()
    wb.active.title = "1_Banka_ve_Kasa"
    wb.create_sheet("2_Musteri_Alacaklari")
    buf = io.BytesIO()
    wb.save(buf)
    try:
        V.oku(buf.getvalue())
        assert False
    except V.SablonHatasi as e:
        assert "eski şablon" in str(e)


def _calistir(**ayar):
    at = AppTest.from_file("app.py", default_timeout=60)
    at.run()
    for ad, deger in ayar.items():
        if ad == "gun":
            at.slider[1].set_value(deger)
        elif ad == "iterasyon":
            at.slider[0].set_value(deger)
        elif ad == "kaynak":
            at.toggle[0].set_value(deger)
        elif ad == "erteleme":
            at.toggle[1].set_value(deger)
    at.run()
    assert not at.exception, at.exception
    return at


def test_arayuz_varsayilan():
    _calistir()


def test_arayuz_kaynaksiz_ve_ertelemeli():
    _calistir(kaynak=False, erteleme=True)


def test_arayuz_uzun_projeksiyon_cok_senaryo():
    _calistir(gun=365, iterasyon=10000)
