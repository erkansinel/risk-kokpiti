"""Monte Carlo likidite simülasyon motoru.

Rastgelelik kaynakları
----------------------
* Piyasa faktörü (Zm): her senaryo için tek bir "ekonomi ne kadar kötü" şoku. Kötü piyasada
  müşteriler daha az ve daha geç öder, yeni satış düşer, bankalar kredi yenilemez / limit keser.
* Segment faktörü (Zs): aynı segmentteki müşterilerin ortak şoku.
* Kalem bazlı (idiyosenkratik) şok.
  Tek faktörlü Gauss kopulası: X = √ρm·Zm + √ρs·Zs + √(1−ρm−ρs)·ε ; olay gerçekleşir ⇔ X < Φ⁻¹(p).
* Kur: USD/TRY ve EUR/TRY ortak bir TL değer kaybı yolu izler (geometrik Brown hareketi).

Kaynak kullanımı (finansman sırası)
-----------------------------------
Her gün bakiye minimum nakit tamponunun altına düşerse sırasıyla:
  1) kredi limitleri (en düşük faizliden başlayarak, kısmi çekim),
  2) yönetim aksiyonları (öncelik sırasıyla, tek seferde tamamı).
Bakiye tamponun üzerine çıkınca çekilen krediler en pahalıdan başlayarak geri ödenir.
Çekilen kredinin faizi günlük işler.
"""
import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import NormalDist

import numpy as np
import pandas as pd

from veri import Veri

PHI_INV = NormalDist().inv_cdf

KAT_TAHSILAT = "Müşteri Tahsilatı"
KAT_SATIS = "Yeni Satış"
KAT_TEDARIK = "Tedarikçi Ödemesi"
KAT_GIDER = "Sabit Gider"
KAT_FINANSMAN = "Kredi / Leasing"
KAT_DIGER = "Diğer Çıkış"
KAT_KUR = "Döviz Kur Farkı"
KAT_LIMIT = "Limit Kullanımı (net)"
KAT_AKSIYON = "Yönetim Aksiyonu"
KAT_LIMIT_FAIZ = "Limit Faizi"
AKIS_KATEGORILERI = [KAT_TAHSILAT, KAT_SATIS, KAT_TEDARIK, KAT_GIDER, KAT_FINANSMAN, KAT_DIGER]
KAYNAK_KATEGORILERI = [KAT_LIMIT, KAT_AKSIYON, KAT_LIMIT_FAIZ]


@dataclass(frozen=True)
class Ayarlar:
    iterasyon: int = 1000
    gun: int = 90
    tohum: int = 42
    borc_erteleme: bool = False        # True: ertelenebilir borçlar maks. ertelemede ödenir (iyimser)
    rho_piyasa: float = 0.30           # müşteriler arası ortak piyasa korelasyonu
    rho_segment: float = 0.20          # aynı segment içi ek korelasyon
    kur_artis: float = 0.25            # yıllık beklenen TL değer kaybı (0.25 = %25)
    kur_oynaklik: float = 0.15         # yıllık kur oynaklığı
    kaynak_kullan: bool = True


@dataclass
class Sonuc:
    tarihler: pd.DatetimeIndex
    bakiye_ham: np.ndarray            # (n, G) kaynak kullanılmadan
    bakiye: np.ndarray                # (n, G) kaynaklar kullanılarak
    baslangic_nakdi: float            # TRY, analiz günü kuruyla
    tampon: float
    limit_kapasitesi: float           # nominal kullanılabilir limit toplamı
    kategori: dict                    # kategori -> (G,) senaryo ortalaması günlük akış
    kaynak_raporu: pd.DataFrame
    acik_kredi: np.ndarray            # (n,) dönem sonunda geri ödenmemiş limit kullanımı
    faiz_maliyeti: np.ndarray         # (n,)
    finansman_ihtiyaci: np.ndarray    # (n,) tamponu korumak için gereken ek kaynak (kaynaksız)
    aksiyonsuz_kaynak_var: bool = field(default=False)


def aylik_odeme_gunleri(bas: date, odeme_gunu: int, gun_sayisi: int):
    """Ayın X. günündeki ödemelerin gün indeksleri. Ay kısaysa ayın son günü."""
    bitis = bas + timedelta(days=gun_sayisi - 1)
    y, m, sonuc = bas.year, bas.month, []
    while date(y, m, 1) <= bitis:
        t = date(y, m, min(int(odeme_gunu), calendar.monthrange(y, m)[1]))
        i = (t - bas).days
        if 0 <= i < gun_sayisi:
            sonuc.append(i)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return sonuc


def _esik(p):
    """Olasılık p için kopula eşiği. p<=0 → hiç, p>=1 → her zaman."""
    if p <= 0:
        return -np.inf
    if p >= 1:
        return np.inf
    return PHI_INV(p)


def simule_et(v: Veri, a: Ayarlar) -> Sonuc:
    rng = np.random.default_rng(a.tohum)
    n, G = a.iterasyon, a.gun
    bas = v.analiz_tarihi
    satir = np.arange(n)
    T = v.tablolar

    def gi(t):  # tarih -> gün indeksi
        return (t - bas).days

    rho_m = float(np.clip(a.rho_piyasa, 0, 0.95))
    rho_s = float(np.clip(a.rho_segment, 0, 0.95 - rho_m))
    sm, ss, se = np.sqrt(rho_m), np.sqrt(rho_s), np.sqrt(max(1 - rho_m - rho_s, 0))
    se_m = np.sqrt(1 - rho_m)
    Zm = rng.standard_normal(n)

    # ---------------- Kur yolları ----------------
    t = np.arange(G) / 365.0
    W = np.zeros((n, G))
    if G > 1:
        W[:, 1:] = np.cumsum(rng.standard_normal((n, G - 1)) * np.sqrt(1 / 365.0), axis=1)
    mu = np.log1p(a.kur_artis)
    carpan = np.exp((mu - 0.5 * a.kur_oynaklik ** 2) * t + a.kur_oynaklik * W)
    kurlar = {p: (v.kur(p) or 0) * carpan for p in ("USD", "EUR")}

    def kur_gun(para, d):
        """Sabit gün d için (n,) kur vektörü."""
        return np.ones(n) if para == "TRY" else kurlar[para][:, d]

    def kur_vek(para, gunler):
        """Senaryo başına farklı gün için (n,) kur vektörü (gün G'yi aşarsa son gün)."""
        return np.ones(n) if para == "TRY" else kurlar[para][satir, np.minimum(gunler, G - 1)]

    toplam = np.zeros((n, G))
    kat = {k: np.zeros(G) for k in AKIS_KATEGORILERI + [KAT_KUR] + KAYNAK_KATEGORILERI}

    def ekle_sabit(k, d, vek):
        if 0 <= d < G:
            toplam[:, d] += vek
            kat[k][d] += vek.sum()

    def ekle_degisken(k, gunler, vek, maske):
        m = maske & (gunler < G)
        np.add.at(toplam, (satir[m], gunler[m]), vek[m])
        np.add.at(kat[k], gunler[m], vek[m])

    # ---------------- Başlangıç nakdi (döviz hesaplar kurla yeniden değerlenir) ----------------
    banka = T["1_Banka_ve_Kasa"]
    baz = np.zeros((n, G))
    baslangic_nakdi = 0.0
    for _, r in banka.iterrows():
        tutar = max(r["Bakiye"] - (r["Bloke Tutar"] or 0), 0)
        if r["Para Birimi"] == "TRY":
            baz += tutar
        else:
            baz += tutar * kurlar[r["Para Birimi"]]
        baslangic_nakdi += tutar * (v.kur(r["Para Birimi"]) or 0)
    kat[KAT_KUR][1:] = np.diff(baz, axis=1).sum(axis=0)

    # ---------------- Müşteri alacakları ----------------
    al = T["2_Musteri_Alacaklari"]
    if len(al):
        segmentler = {s: i for i, s in enumerate(sorted(al["Segment"].astype(str).unique()))}
        Zs = rng.standard_normal((n, len(segmentler)))
        for _, r in al.iterrows():
            p = r["Tahsilat İhtimali (%)"] / 100
            if p <= 0:
                continue
            zs = Zs[:, segmentler[str(r["Segment"])]]
            ortak = sm * Zm + ss * zs
            tahsil = (ortak + se * rng.standard_normal(n)) < _esik(p)
            # kötü piyasa (düşük Z) → daha uzun gecikme
            gecikme = r["Ortalama Gecikme (Gün)"] + r["Gecikme Belirsizliği (± Gün)"] * (
                -ortak + se * rng.standard_normal(n))
            gun = np.maximum(gi(r["Vade Tarihi"]) + np.rint(np.maximum(gecikme, 0)).astype(int), 1)
            ekle_degisken(KAT_TAHSILAT, gun, r["Tutar"] * kur_vek(r["Para Birimi"], gun), tahsil)

    # ---------------- Yeni satış tahmini ----------------
    for _, r in T["8_Satis_Tahmini"].iterrows():
        ay = r["Ay"]
        ay_bas = date(ay.year, ay.month, 1)
        ay_son = date(ay.year, ay.month, calendar.monthrange(ay.year, ay.month)[1])
        bas_g, son_g = max(gi(ay_bas), 0), gi(ay_son)
        if son_g < 0 or bas_g >= G:
            continue
        gun_basi = r["Beklenen Tahsilat"] / (son_g - bas_g + 1)  # ay içine (kalan günlere) eşit yayılır
        f = np.maximum(1 + r["Belirsizlik (± %)"] / 100 * (sm * Zm + se_m * rng.standard_normal(n)), 0)
        d1 = min(son_g, G - 1)
        dilim = slice(bas_g, d1 + 1)
        kur = 1.0 if r["Para Birimi"] == "TRY" else kurlar[r["Para Birimi"]][:, dilim]
        ek = (f[:, None] * gun_basi) * kur
        toplam[:, dilim] += ek
        kat[KAT_SATIS][dilim] += ek.sum(axis=0)

    # ---------------- Tedarikçi borçları ----------------
    for _, r in T["3_Tedarikci_Borclari"].iterrows():
        d = gi(r["Vade Tarihi"])
        ertelenebilir = r["Kritik Tedarikçi"] != "Evet" and r["Ödeme Aracı"] != "Verilen Çek"
        if a.borc_erteleme and ertelenebilir:
            d += int(r["Maks. Erteleme (Gün)"])
        d = max(d, 0)
        if d < G:
            ekle_sabit(KAT_TEDARIK, d, -r["Tutar"] * kur_gun(r["Para Birimi"], d))

    # ---------------- Sabit giderler ----------------
    for _, r in T["4_Sabit_Giderler"].iterrows():
        for d in aylik_odeme_gunleri(bas, r["Ödeme Günü"], G):
            tarih = bas + timedelta(days=d)
            if r["Başlangıç Tarihi"] and tarih < r["Başlangıç Tarihi"]:
                continue
            if r["Bitiş Tarihi"] and tarih > r["Bitiş Tarihi"]:
                continue
            tutar = r["Aylık Tutar"]
            if r["Artış Tarihi"] and tarih >= r["Artış Tarihi"]:
                tutar *= 1 + r["Artış Oranı (%)"] / 100
            ekle_sabit(KAT_GIDER, d, -tutar * kur_gun(r["Para Birimi"], d))

    # ---------------- Kredi / leasing ödemeleri ----------------
    for _, r in T["5_Finansman_Odemeleri"].iterrows():
        d = max(gi(r["Ödeme Tarihi"]), 0)
        if d >= G:
            continue
        cikis = np.full(n, r["Anapara"] + r["Faiz"], dtype=float)
        if r["Yenilenebilir"] == "Evet" and r["Yenilenme İhtimali (%)"] > 0:
            yenilendi = (sm * Zm + se_m * rng.standard_normal(n)) < _esik(r["Yenilenme İhtimali (%)"] / 100)
            cikis = np.where(yenilendi, r["Faiz"], cikis)
        ekle_sabit(KAT_FINANSMAN, d, -cikis * kur_gun(r["Para Birimi"], d))

    # ---------------- Diğer çıkışlar ----------------
    for _, r in T["9_Diger_Cikislar"].iterrows():
        d = max(gi(r["Tarih"]), 0)
        ekle_sabit(KAT_DIGER, d, -r["Tutar"] * kur_gun(r["Para Birimi"], d))

    bakiye_ham = baz + np.cumsum(toplam, axis=1)
    tampon = float(v.parametre.get("Minimum Nakit Tamponu (TRY)") or 0)
    finansman_ihtiyaci = np.maximum(tampon - bakiye_ham.min(axis=1), 0)

    # ---------------- Kaynaklar ----------------
    lim = T["6_Kredi_Limitleri"]
    lim = lim[lim["Kullanılsın"] == "Evet"].sort_values("Yıllık Faiz (%)", kind="stable")
    akt = T["7_Yonetim_Aksiyonlari"]
    akt = akt[akt["Kullanılsın"] == "Evet"].sort_values("Öncelik", kind="stable")
    L, A = len(lim), len(akt)

    kapasite = (lim["Toplam Limit (TRY)"] - lim["Kullanılan (TRY)"]).clip(lower=0).to_numpy(float)
    oran = lim["Yıllık Faiz (%)"].to_numpy(float) / 100 / 365
    kullanilabilir = np.zeros((n, L))
    for i, (_, r) in enumerate(lim.iterrows()):
        kesildi = (sm * Zm + se_m * rng.standard_normal(n)) < _esik(r["Kesilme İhtimali (%)"] / 100)
        kullanilabilir[:, i] = np.where(kesildi, 0, kapasite[i])

    net = (akt["Tutar (TRY)"] * (1 - akt["Kayıp / İskonto (%)"] / 100)).to_numpy(float)
    en_erken = np.array([max(gi(t), 0) for t in akt["En Erken Tarih"]], dtype=int)
    gerceklesir = rng.random((n, A)) < (akt["Gerçekleşme İhtimali (%)"].to_numpy(float) / 100)

    cekilen = np.zeros((n, L))
    max_cekilen = np.zeros((n, L))
    lim_ilk = np.full((n, L), -1)
    akt_gun = np.full((n, A), -1)
    faiz_top = np.zeros(n)
    F = np.zeros(n)
    bakiye = bakiye_ham.copy()

    if a.kaynak_kullan and (L or A):
        for d in range(G):
            faiz = cekilen @ oran if L else np.zeros(n)
            F -= faiz
            faiz_top += faiz
            kat[KAT_LIMIT_FAIZ][d] -= faiz.sum()
            ihtiyac = tampon - (bakiye_ham[:, d] + F)

            for i in range(L):
                m = ihtiyac > 0
                if not m.any():
                    break
                cek = np.where(m, np.clip(np.minimum(ihtiyac, kullanilabilir[:, i] - cekilen[:, i]), 0, None), 0)
                cekilen[:, i] += cek
                F += cek
                ihtiyac -= cek
                kat[KAT_LIMIT][d] += cek.sum()
                yeni = (cek > 0) & (lim_ilk[:, i] < 0)
                lim_ilk[yeni, i] = d

            for j in range(A):
                m = (ihtiyac > 0) & (akt_gun[:, j] < 0) & gerceklesir[:, j] & (d >= en_erken[j])
                if m.any():
                    F[m] += net[j]
                    ihtiyac[m] -= net[j]
                    akt_gun[m, j] = d
                    kat[KAT_AKSIYON][d] += net[j] * m.sum()

            fazla = -ihtiyac
            for i in reversed(range(L)):  # en pahalı krediyi önce kapat
                m = fazla > 0
                if not m.any():
                    break
                ode = np.where(m, np.minimum(fazla, cekilen[:, i]), 0)
                cekilen[:, i] -= ode
                F -= ode
                fazla -= ode
                kat[KAT_LIMIT][d] -= ode.sum()

            np.maximum(max_cekilen, cekilen, out=max_cekilen)
            bakiye[:, d] = bakiye_ham[:, d] + F

    # ---------------- Kaynak raporu ----------------
    satirlar = []
    for i, (_, r) in enumerate(lim.iterrows()):
        kullanan = max_cekilen[:, i] > 0
        satirlar.append({
            "Kaynak": f"{r['Banka']} · {r['Limit Türü']}",
            "Grup": "Kredi Limiti",
            "Kapasite": kapasite[i],
            "Koşul": f"%{r['Yıllık Faiz (%)']:.0f} faiz · %{r['Kesilme İhtimali (%)']:.0f} kesilme riski",
            "Kullanılma Olasılığı": kullanan.mean() * 100,
            "Medyan Kullanım": float(np.median(max_cekilen[kullanan, i])) if kullanan.any() else 0.0,
            "Kötü Senaryo Kullanımı": float(np.percentile(max_cekilen[:, i], 95)),
            "İlk Kullanım Günü": float(np.median(lim_ilk[kullanan, i])) if kullanan.any() else None,
        })
    for j, (_, r) in enumerate(akt.iterrows()):
        kullanan = akt_gun[:, j] >= 0
        satirlar.append({
            "Kaynak": r["Aksiyon"],
            "Grup": r["Tür"],
            "Kapasite": net[j],
            "Koşul": f"{r['En Erken Tarih']:%d.%m.%Y} sonrası · %{r['Gerçekleşme İhtimali (%)']:.0f} gerçekleşme"
                     + (f" · %{r['Kayıp / İskonto (%)']:.0f} kayıp" if r["Kayıp / İskonto (%)"] else ""),
            "Kullanılma Olasılığı": kullanan.mean() * 100,
            "Medyan Kullanım": net[j] if kullanan.any() else 0.0,
            "Kötü Senaryo Kullanımı": net[j] if np.mean(kullanan) >= 0.05 else 0.0,
            "İlk Kullanım Günü": float(np.median(akt_gun[kullanan, j])) if kullanan.any() else None,
        })
    rapor = pd.DataFrame(satirlar, columns=["Kaynak", "Grup", "Kapasite", "Koşul", "Kullanılma Olasılığı",
                                            "Medyan Kullanım", "Kötü Senaryo Kullanımı", "İlk Kullanım Günü"])

    return Sonuc(
        tarihler=pd.date_range(bas, periods=G, freq="D"),
        bakiye_ham=bakiye_ham,
        bakiye=bakiye,
        baslangic_nakdi=baslangic_nakdi,
        tampon=tampon,
        limit_kapasitesi=float(kapasite.sum()),
        kategori={k: s / n for k, s in kat.items()},
        kaynak_raporu=rapor,
        acik_kredi=cekilen.sum(axis=1),
        faiz_maliyeti=faiz_top,
        finansman_ihtiyaci=finansman_ihtiyaci,
        aksiyonsuz_kaynak_var=bool(L or A),
    )
