"""Motor testleri:  python -m pytest -q test_motor.py"""
import time
from datetime import date

import numpy as np
import pandas as pd
import pytest

import veri as V
from motor import KAYNAK_KATEGORILERI, Ayarlar, simule_et
from sablon import sablon_olustur
from sema import SAYFALAR

BAS = date(2026, 11, 18)


def yap(param=None, **sayfalar):
    """Şemaya uygun küçük bir test verisi kurar. Eksik opsiyonel kolonlar varsayılanla doldurulur."""
    p = {"Şirket Unvanı": "Test", "Analiz Tarihi": BAS, "USD/TRY Kuru": 40.0, "EUR/TRY Kuru": 45.0,
         "Minimum Nakit Tamponu (TRY)": 0}
    p.update(param or {})
    t = {}
    for s in SAYFALAR:
        satirlar = []
        for r in sayfalar.get(s.ad, []):
            satirlar.append({k.ad: r.get(k.ad, k.varsayilan) for k in s.kolonlar} | {"_satir": 0})
        t[s.ad] = pd.DataFrame(satirlar, columns=[k.ad for k in s.kolonlar] + ["_satir"])
    return V.Veri(p, t, [])


def kasa(tutar, para="TRY"):
    return [{"Hesap": "K", "Para Birimi": para, "Bakiye": tutar, "Bloke Tutar": 0}]


def test_deterministik_senaryo_elle_hesapla():
    v = yap(**{
        "1_Banka_ve_Kasa": kasa(1000),
        "2_Musteri_Alacaklari": [{"Müşteri": "M", "Segment": "G", "Para Birimi": "TRY", "Tutar": 500,
                                  "Vade Tarihi": date(2026, 11, 28), "Tahsilat İhtimali (%)": 100,
                                  "Ortalama Gecikme (Gün)": 0, "Gecikme Belirsizliği (± Gün)": 0}],
        "3_Tedarikci_Borclari": [{"Tedarikçi": "T", "Para Birimi": "TRY", "Tutar": 300,
                                  "Vade Tarihi": date(2026, 11, 10)}],          # vadesi geçmiş → 0. gün
        "4_Sabit_Giderler": [{"Gider Kalemi": "Maaş", "Para Birimi": "TRY", "Aylık Tutar": 200,
                              "Ödeme Günü": 1, "Artış Tarihi": date(2027, 1, 1), "Artış Oranı (%)": 50}],
    })
    s = simule_et(v, Ayarlar(iterasyon=50, gun=60, kaynak_kullan=False))
    b = s.bakiye_ham
    assert np.allclose(b[:, 0], 700)            # 1000 - 300 (gecikmiş borç bugün)
    assert np.allclose(b[:, 10], 1200)          # 28.11 tahsilat
    assert np.allclose(b[:, 13], 1000)          # 01.12 maaş = 13. gün (takvim)
    assert np.allclose(b[:, 44], 700)           # 01.01 maaş zamlı: 300
    assert np.allclose(b[:, 59], 700)


def test_nakit_korunumu_ornek_dosya():
    v = V.oku(sablon_olustur(ornek=True))
    s = simule_et(v, Ayarlar(iterasyon=400, gun=120))
    akis = sum(seri.sum() for k, seri in s.kategori.items() if k not in KAYNAK_KATEGORILERI)
    assert s.bakiye_ham[:, -1].mean() == pytest.approx(s.baslangic_nakdi + akis, rel=1e-9)
    kaynak = sum(s.kategori[k].sum() for k in KAYNAK_KATEGORILERI)
    assert s.bakiye[:, -1].mean() == pytest.approx(s.bakiye_ham[:, -1].mean() + kaynak, rel=1e-9)


def test_verilen_cek_ve_kritik_ertelenmez():
    ortak = {"Para Birimi": "TRY", "Tutar": 100, "Vade Tarihi": date(2026, 11, 20), "Maks. Erteleme (Gün)": 30}
    v = yap(**{"1_Banka_ve_Kasa": kasa(1000), "3_Tedarikci_Borclari": [
        ortak | {"Tedarikçi": "Çek", "Ödeme Aracı": "Verilen Çek"},
        ortak | {"Tedarikçi": "Kritik", "Kritik Tedarikçi": "Evet"},
        ortak | {"Tedarikçi": "Normal"},
    ]})
    s = simule_et(v, Ayarlar(iterasyon=10, gun=60, borc_erteleme=True, kaynak_kullan=False))
    assert np.allclose(s.bakiye_ham[:, 2], 800)   # çek + kritik vadede
    assert np.allclose(s.bakiye_ham[:, 32], 700)  # normal 30 gün ertelendi


def test_korelasyon_kuyrugu_kalinlastirir():
    alacaklar = [{"Müşteri": f"M{i}", "Segment": "G", "Para Birimi": "TRY", "Tutar": 100,
                  "Vade Tarihi": date(2026, 12, 1), "Tahsilat İhtimali (%)": 80} for i in range(40)]
    v = yap(**{"1_Banka_ve_Kasa": kasa(0), "2_Musteri_Alacaklari": alacaklar})
    p5 = {}
    for rho in (0.0, 0.5):
        s = simule_et(v, Ayarlar(iterasyon=4000, gun=30, rho_piyasa=rho, rho_segment=0, kaynak_kullan=False))
        son = s.bakiye_ham[:, -1]
        assert son.mean() == pytest.approx(3200, rel=0.03)   # beklenen değer korelasyondan bağımsız
        p5[rho] = np.percentile(son, 5)
    assert p5[0.5] < p5[0.0] - 500                          # ama kötü senaryo çok daha kötü


def test_kaynaklar_tamponu_korur_ve_geri_odenir():
    v = yap({"Minimum Nakit Tamponu (TRY)": 100}, **{
        "1_Banka_ve_Kasa": kasa(500),
        "9_Diger_Cikislar": [{"Açıklama": "Vergi", "Para Birimi": "TRY", "Tutar": 1000, "Tarih": date(2026, 11, 25)}],
        "2_Musteri_Alacaklari": [{"Müşteri": "M", "Segment": "G", "Para Birimi": "TRY", "Tutar": 2000,
                                  "Vade Tarihi": date(2026, 12, 15), "Tahsilat İhtimali (%)": 100}],
        "6_Kredi_Limitleri": [{"Banka": "B", "Limit Türü": "Rotatif Kredi", "Toplam Limit (TRY)": 5000,
                               "Yıllık Faiz (%)": 36.5}],
    })
    s = simule_et(v, Ayarlar(iterasyon=20, gun=40))
    assert (s.bakiye_ham.min(axis=1) < 0).all()
    assert (s.bakiye >= 100 - 1e-6).all()                    # tampon korundu
    assert np.allclose(s.acik_kredi, 0)                      # tahsilatla kredi kapandı
    # 600 TL × 20 gün × %0,1 günlük ≈ 12 TL faiz
    assert s.faiz_maliyeti.mean() == pytest.approx(600 * 0.001 * 20, rel=0.05)


def test_doviz_kalemleri_kurla_cevrilir():
    v = yap(**{"1_Banka_ve_Kasa": kasa(100, "USD")})
    s = simule_et(v, Ayarlar(iterasyon=3000, gun=181, kur_artis=0.20, kur_oynaklik=0.10, kaynak_kullan=False))
    assert s.baslangic_nakdi == 4000
    assert s.bakiye_ham[:, -1].mean() == pytest.approx(4000 * 1.2 ** (180 / 365), rel=0.01)


def test_hiz():
    v = V.oku(sablon_olustur(ornek=True))
    t0 = time.time()
    simule_et(v, Ayarlar(iterasyon=5000, gun=180))
    assert time.time() - t0 < 10
