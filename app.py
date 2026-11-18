"""Likidite Kokpiti — Monte Carlo nakit akışı stres testi.

Çalıştırma:  streamlit run app.py
"""
import hashlib
import os
from dataclasses import astuple
from datetime import timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import veri as V
from motor import AKIS_KATEGORILERI, KAT_AKSIYON, KAT_KUR, KAT_LIMIT, KAT_LIMIT_FAIZ, Ayarlar, simule_et
from sablon import sablon_olustur
from stil import C, CSS, FONT, KATEGORI_RENK

st.set_page_config(page_title="Likidite Kokpiti", page_icon="📊", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown(CSS, unsafe_allow_html=True)

# Varsayılan Excel: önce uygulama klasörü, sonra eski veri klasörü
_ADAYLAR = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "Likidite_Sablonu.xlsx"),
            r"C:\Programlarim\montecarlo\montecarlo_veri\Likidite_Sablonu.xlsx"]
VARSAYILAN_YOL = next((p for p in _ADAYLAR if os.path.exists(p)), _ADAYLAR[0])
AYLAR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
PLOT_CFG = {"displayModeBar": False, "responsive": True}


# ============================================================
# Yardımcılar
# ============================================================
def tl(x):
    return f"{x:,.0f}".replace(",", ".")


def tl_kisa(x):
    a = abs(x)
    if a >= 1e6:
        return f"{x/1e6:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " Mn"
    if a >= 1e3:
        return f"{x/1e3:,.0f}".replace(",", ".") + " Bin"
    return tl(x)


def yuzde(x, ondalik=0):
    return f"%{x:.{ondalik}f}".replace(".", ",")


@st.cache_data(show_spinner=False)
def sablon_bayt(ornek):
    return sablon_olustur(ornek)


@st.cache_data(show_spinner=False)
def veriyi_oku(kaynak, anahtar):
    return V.oku(kaynak)


@st.cache_data(show_spinner=False, max_entries=20)
def simulasyon(anahtar, _veri, ayar_tuple):
    return simule_et(_veri, Ayarlar(*ayar_tuple))


def ilk_gun(maske):
    i = np.flatnonzero(maske)
    return int(i[0]) if i.size else None


# ============================================================
# Üst kontrol şeridi
# ============================================================
if "tohum" not in st.session_state:
    st.session_state.tohum = 42

with st.container(key="kontrol"):
    c1, c2, c3, c4, c5 = st.columns([1.35, 1.2, 1.2, 0.75, 0.75], gap="medium", vertical_alignment="bottom")
    with c1:
        st.markdown(
            f"<div style='font-size:1.2rem;font-weight:800;color:{C['text']};letter-spacing:-.3px'>📊 Likidite Kokpiti</div>"
            f"<div style='font-size:.75rem;color:{C['muted']};margin:2px 0 10px 0'>Monte Carlo Nakit Akışı Stres Testi</div>",
            unsafe_allow_html=True)
    with c2:
        iterasyon = st.slider("İterasyon", 500, 10000, 2000, 500)
    with c3:
        gun = st.slider("Projeksiyon (Gün)", 30, 365, 90, 15)
    with c4:
        with st.popover("⚙️ Varsayımlar", width="stretch"):
            st.markdown("**Model varsayımları**")
            kaynak_kullan = st.toggle("Limit ve yönetim aksiyonlarını kullan", True,
                                      help="Açıkken bakiye tamponun altına düşünce model kaynakları sırayla kullanır.")
            borc_erteleme = st.toggle("Tedarikçi ödemelerini maks. ertelemede yap (iyimser)", False,
                                      help="Kapalıyken borçlar sözleşme vadesinde ödenir (stres varsayımı). "
                                           "Kritik tedarikçi ve verilen çek hiçbir zaman ertelenmez.")
            rho_m = st.slider("Piyasa korelasyonu", 0.0, 0.8, 0.30, 0.05,
                              help="Müşterilerin krizde birlikte gecikme / ödememe eğilimi. 0 = bağımsız.")
            rho_s = st.slider("Segment içi ek korelasyon", 0.0, 0.5, 0.20, 0.05,
                              help="Aynı segmentteki müşterilerin ek ortak riski.")
            kur_artis = st.slider("Yıllık beklenen kur artışı (%)", 0, 100, 25, 5) / 100
            kur_vol = st.slider("Yıllık kur oynaklığı (%)", 0, 60, 15, 5) / 100
    with c5:
        if st.button("🎲 Yeniden Simüle Et", type="primary", width="stretch"):
            st.session_state.tohum = int(np.random.randint(0, 1_000_000))

    d1, d2, d3 = st.columns([2.6, 0.75, 0.75], gap="medium", vertical_alignment="bottom")
    with d1:
        yuklenen = st.file_uploader("Şirket Excel'i (.xlsx)", type=["xlsx"])
    with d2:
        st.download_button("📥 Boş Şablon", sablon_bayt(False), "Likidite_Sablonu.xlsx", width="stretch",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with d3:
        st.download_button("📄 Örnek Dosya", sablon_bayt(True), "Likidite_Sablonu_ORNEK.xlsx", width="stretch",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ============================================================
# Veri
# ============================================================
kaynak_notu = None
if yuklenen is not None:
    ham = yuklenen.getvalue()
    kaynak, anahtar = ham, hashlib.md5(ham).hexdigest()
elif os.path.exists(VARSAYILAN_YOL):
    kaynak, anahtar = VARSAYILAN_YOL, f"{VARSAYILAN_YOL}:{os.path.getmtime(VARSAYILAN_YOL)}"
else:
    kaynak, anahtar = sablon_bayt(True), "ornek"
    kaynak_notu = "Örnek veri gösteriliyor. Kendi verinizle çalışmak için şablonu indirip doldurun ve yükleyin."

try:
    v = veriyi_oku(kaynak, anahtar)
except V.SablonHatasi as e:
    if yuklenen is None and kaynak != "ornek":
        kaynak_notu = f"`{VARSAYILAN_YOL}` okunamadı ({e}) Örnek veri gösteriliyor."
        v, anahtar = veriyi_oku(sablon_bayt(True), "ornek"), "ornek"
    else:
        st.error(f"**Dosya okunamadı.** {e}")
        st.stop()

ayar = Ayarlar(iterasyon=iterasyon, gun=gun, tohum=st.session_state.tohum, borc_erteleme=borc_erteleme,
               rho_piyasa=rho_m, rho_segment=rho_s, kur_artis=kur_artis, kur_oynaklik=kur_vol,
               kaynak_kullan=kaynak_kullan)
s = simulasyon(anahtar, v, astuple(ayar))

bas = v.analiz_tarihi
tampon = s.tampon


def tarih_str(i):
    t = bas + timedelta(days=int(i))
    return f"{t.day} {AYLAR[t.month - 1]}"


# Uygulama düzeyinde ek veri kontrolü: satış tahmini projeksiyonu kapsıyor mu?
bulgular = list(v.bulgular)
satis = v.tablolar["8_Satis_Tahmini"]
son_tarih = bas + timedelta(days=gun - 1)
if len(satis):
    son_ay = max(satis["Ay"])
    if (son_ay.year, son_ay.month) < (son_tarih.year, son_tarih.month):
        bulgular.append(V.Bulgu("uyari", "8_Satis_Tahmini",
                                f"Satış tahmini {AYLAR[son_ay.month-1]} {son_ay.year} ayında bitiyor, projeksiyon "
                                f"{son_tarih:%d.%m.%Y} tarihine kadar. Sonraki aylarda yeni satış sıfır kabul ediliyor."))

# ============================================================
# Metrikler
# ============================================================
kaynakli = kaynak_kullan and s.aksiyonsuz_kaynak_var
B = s.bakiye if kaynakli else s.bakiye_ham
p5, p25, p50, p75, p95 = np.percentile(B, [5, 25, 50, 75, 95], axis=0)
h5, h50 = np.percentile(s.bakiye_ham, [5, 50], axis=0)

temerrut = float((B < 0).any(axis=1).mean() * 100)
temerrut_ham = float((s.bakiye_ham < 0).any(axis=1).mean() * 100)
ihtiyac_p95 = float(np.percentile(s.finansman_ihtiyaci, 95))
ihtiyac_p50 = float(np.median(s.finansman_ihtiyaci))
ilk_ihtiyac = ilk_gun(h5 < tampon)          # kötü senaryoda tampon delinmeye başlıyor
ilk_risk = ilk_gun(p5 < 0)                  # gösterilen seride %5 alt sınır eksiye
ilk_kriz = ilk_gun(p50 < 0)                 # gösterilen seride medyan eksiye
kapanis = float(p50[-1])
acik_kredi = float(np.median(s.acik_kredi))
faiz = float(s.faiz_maliyeti.mean())
kalan_acik = float(np.percentile(np.maximum(-B.min(axis=1), 0), 95))

# ============================================================
# Başlık
# ============================================================
hata_say = sum(b.seviye == "hata" for b in bulgular)
uyari_say = sum(b.seviye == "uyari" for b in bulgular)
cip = ""
if hata_say:
    cip = f"<span class='pill pill-red'>⛔ {hata_say} veri hatası</span>"
elif uyari_say:
    cip = f"<span class='pill pill-amber'>⚠️ {uyari_say} veri uyarısı</span>"
else:
    cip = "<span class='pill pill-green'>✓ Veri kontrolleri temiz</span>"
st.markdown(
    f"<div style='margin:18px 2px 14px 2px;display:flex;align-items:center;gap:12px;flex-wrap:wrap'>"
    f"<span style='font-size:1.3rem;font-weight:800;color:{C['text']};letter-spacing:-.4px'>{v.parametre['Şirket Unvanı']}</span>"
    f"<span style='color:{C['muted']};font-size:.9rem'>{bas:%d.%m.%Y} itibarıyla {gun} günlük nakit stres analizi · "
    f"{tl(iterasyon)} senaryo · tampon {tl_kisa(tampon)} ₺</span>{cip}</div>",
    unsafe_allow_html=True)
if kaynak_notu:
    st.info(kaynak_notu, icon="ℹ️")
if hata_say:
    ilk_hatalar = [b for b in bulgular if b.seviye == "hata"][:3]
    st.error("**Sonuçlar eksik veriyle hesaplandı.** Hatalı satırlar hesaba katılmadı ve kuru girilmeyen döviz "
             "kalemleri sıfır sayıldı. Excel'i düzeltip tekrar yükleyin:\n\n"
             + "\n".join(f"- **{b.sayfa}** — {b.mesaj}" for b in ilk_hatalar)
             + (f"\n\nTümü sayfa sonundaki *Veri kontrolleri* bölümünde ({hata_say} hata)." if hata_say > 3 else ""),
             icon="⛔")


# ============================================================
# KPI kartları
# ============================================================
def kpi(baslik, deger, birim, pill_cls, pill_txt, accent):
    return (f"<div class='kpi' style='--accent:{accent}'><div class='kpi-t'>{baslik}</div>"
            f"<div class='kpi-v'>{deger}<small>{birim}</small></div>"
            f"<div class='pill {pill_cls}' title='{pill_txt}'>{pill_txt}</div></div>")


k1, k2, k3, k4 = st.columns(4, gap="medium")
k1.markdown(kpi("Başlangıç Likiditesi", tl_kisa(s.baslangic_nakdi + s.limit_kapasitesi), "TRY", "pill-blue",
                f"Nakit {tl_kisa(s.baslangic_nakdi)} + boş limit {tl_kisa(s.limit_kapasitesi)}", C["blue"]),
            unsafe_allow_html=True)

net = kapanis - s.baslangic_nakdi
k2.markdown(kpi("Dönem Sonu Nakit (Medyan)", tl_kisa(kapanis), "TRY",
                "pill-green" if net >= 0 else "pill-red",
                f"{'▲ +' if net >= 0 else '▼ '}{tl_kisa(net)} net" + (f" · {tl_kisa(acik_kredi)} açık kredi" if acik_kredi > 0 else ""),
                C["green"] if net >= 0 else C["red"]), unsafe_allow_html=True)

if ihtiyac_p95 > 0:
    k3.markdown(kpi("Finansman İhtiyacı (Kötü Senaryo)", tl_kisa(ihtiyac_p95), "TRY",
                    "pill-amber" if ihtiyac_p95 <= s.limit_kapasitesi else "pill-red",
                    f"Başlangıç: {ilk_ihtiyac}. gün ({tarih_str(ilk_ihtiyac)}) · medyan {tl_kisa(ihtiyac_p50)}",
                    C["amber"] if ihtiyac_p95 <= s.limit_kapasitesi else C["red"]), unsafe_allow_html=True)
else:
    k3.markdown(kpi("Finansman İhtiyacı", "0", "TRY", "pill-green", "Tampon kötü senaryoda bile korunuyor",
                    C["green"]), unsafe_allow_html=True)

risk_renk = C["red"] if temerrut > 50 else (C["amber"] if temerrut > 10 else C["green"])
risk_cls = "pill-red" if temerrut > 50 else ("pill-amber" if temerrut > 10 else "pill-green")
risk_etiket = "Yüksek risk" if temerrut > 50 else ("Orta risk" if temerrut > 10 else "Düşük risk")
k4.markdown(kpi("Temerrüt Olasılığı" + (" (Kaynaklarla)" if kaynakli else ""), yuzde(temerrut, 1), "", risk_cls,
                (f"Kaynaksız {yuzde(temerrut_ham)} · " if kaynakli else "") + risk_etiket, risk_renk),
            unsafe_allow_html=True)


# ============================================================
# Yönetim kurulu mesajı
# ============================================================
def banner(ikon, baslik, metin, tur):
    renk = {"kirmizi": ("rgba(248,113,113,.35)", "rgba(127,29,29,.45)", "rgba(248,113,113,.18)", "#FCA5A5"),
            "sari": ("rgba(251,191,36,.35)", "rgba(120,53,15,.45)", "rgba(251,191,36,.16)", "#FCD34D"),
            "yesil": ("rgba(52,211,153,.30)", "rgba(6,78,59,.45)", "rgba(52,211,153,.16)", "#6EE7B7")}[tur]
    st.markdown(f"""<div class="banner" style="--bd:{renk[0]};--bg1:{renk[1]};--ic:{renk[2]};--tc:{renk[3]}">
      <div class="ikon">{ikon}</div><div><div class="b1">{baslik}</div><div class="b2">{metin}</div></div></div>""",
                unsafe_allow_html=True)


rapor = s.kaynak_raporu
kullanilan = rapor[rapor["Kullanılma Olasılığı"] >= 20].sort_values("İlk Kullanım Günü")
sira_html = "".join(
    f"<li><b>{r['Kaynak']}</b> — {tl_kisa(r['Medyan Kullanım'])} ₺, ~{tarih_str(r['İlk Kullanım Günü'])} "
    f"(senaryoların {yuzde(r['Kullanılma Olasılığı'])}'inde gerekiyor)</li>"
    for _, r in kullanilan.head(4).iterrows())

if kaynakli:
    if temerrut >= 50:
        banner("🚨", "KIRMIZI ALARM · MEVCUT KAYNAKLAR YETERSİZ",
               f"Tüm limitler ve yönetim aksiyonları kullanılsa bile senaryoların <b>{yuzde(temerrut)}</b>'inde nakit "
               f"eksiye düşüyor{f'; medyan senaryoda <b>{tarih_str(ilk_kriz)}</b> tarihinde' if ilk_kriz is not None else ''}. "
               f"Kötü senaryoda kapatılamayan açık <b>{tl(kalan_acik)} ₺</b>. Yeni finansman, borç yapılandırması "
               f"veya yapısal maliyet önlemi gerekiyor.", "kirmizi")
    elif temerrut >= 10 or ilk_ihtiyac is not None:
        banner("⚠️", "SARI ALARM · KAYNAK PLANI DEVREYE ALINMALI",
               f"Kaynak kullanılmazsa kötü senaryoda nakit <b>{tarih_str(ilk_ihtiyac)}</b> tarihinde tamponun altına iniyor; "
               f"kötü senaryoda gereken ek kaynak <b>{tl(ihtiyac_p95)} ₺</b>. Kaynaklar aşağıdaki sırayla kullanıldığında "
               f"temerrüt olasılığı <b>{yuzde(temerrut_ham)}</b>'den <b>{yuzde(temerrut)}</b>'e iniyor:"
               f"<ol>{sira_html}</ol>", "sari")
    else:
        banner("✅", "YEŞİL ALAN · LİKİDİTE GÜVENLİ",
               f"Kötü senaryolarda bile nakit tamponu korunuyor. Dönem sonu medyan beklentisi <b>{tl(kapanis)} ₺</b>. "
               f"Atıl nakit kısa vadeli araçlarda değerlendirilebilir.", "yesil")
else:
    if ilk_kriz is not None:
        banner("🚨", "KIRMIZI ALARM · ACİL FİNANSMAN GEREKLİ",
               f"Kaynak kullanılmadan medyan senaryoda nakit <b>{tarih_str(ilk_kriz)}</b> tarihinde eksiye düşüyor; "
               f"kötü senaryoda gereken ek kaynak <b>{tl(ihtiyac_p95)} ₺</b>.", "kirmizi")
    elif ilk_risk is not None:
        banner("⚠️", "SARI ALARM · İZLEME VE TAMPON GEREKLİ",
               f"Medyan pozitif, ancak kötü senaryolarda nakit <b>{tarih_str(ilk_risk)}</b> tarihinde eksiye düşüyor. "
               f"Kötü senaryoda gereken ek kaynak <b>{tl(ihtiyac_p95)} ₺</b>.", "sari")
    else:
        banner("✅", "YEŞİL ALAN · LİKİDİTE GÜVENLİ",
               f"Kötü senaryolarda bile bakiye eksiye düşmüyor. Dönem sonu medyan beklentisi <b>{tl(kapanis)} ₺</b>.",
               "yesil")


# ============================================================
# Grafik yardımcıları
# ============================================================
def ortak_layout(fig, yukseklik, **kw):
    fig.update_layout(
        height=yukseklik, font=dict(family=FONT, size=12, color="#CBD5E1"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10, l=10, r=10), separators=",.",
        hoverlabel=dict(bgcolor="#0F172A", bordercolor="#334155", font=dict(family=FONT, size=12, color="#F1F5F9")),
        **kw)
    fig.update_xaxes(showgrid=False, zeroline=False, showline=True, linecolor="rgba(148,163,184,0.25)",
                     tickfont=dict(color=C["muted"], size=11), ticks="outside", ticklen=4,
                     tickcolor="rgba(148,163,184,0.25)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(148,163,184,0.08)", zeroline=False,
                     tickfont=dict(color=C["muted"], size=11), tickformat="~s", ticksuffix=" ₺")
    return fig


def kart_baslik(baslik, alt):
    st.markdown(f"<div class='kart-baslik'>{baslik}</div><div class='kart-alt'>{alt}</div>", unsafe_allow_html=True)


x = s.tarihler

# ============================================================
# Satır 1: Projeksiyon + Temerrüt halkası
# ============================================================
sol, sag = st.columns([2.2, 1], gap="medium")
with sol:
    with st.container(key="kart_ana"):
        kart_baslik("Nakit Bakiyesi Projeksiyonu",
                    ("Kaynaklar kullanılarak · " if kaynakli else "Kaynak kullanılmadan · ")
                    + "bantlar %25–75 ve %5–95 aralığı, her gün için ayrı yüzdelik")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=p95, line=dict(width=0), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=x, y=p5, line=dict(width=0), fill="tonexty", fillcolor="rgba(56,189,248,0.10)",
                                 hoverinfo="skip", name="%5–95"))
        fig.add_trace(go.Scatter(x=x, y=p75, line=dict(width=0), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=x, y=p25, line=dict(width=0), fill="tonexty", fillcolor="rgba(56,189,248,0.20)",
                                 hoverinfo="skip", name="%25–75"))
        fig.add_trace(go.Scatter(x=x, y=p5, name="%5 alt sınır", line=dict(color=C["red"], width=1.3, dash="dot"),
                                 hovertemplate="%{y:,.0f} ₺"))
        if kaynakli:
            fig.add_trace(go.Scatter(x=x, y=h50, name="Kaynaksız medyan",
                                     line=dict(color=C["slate"], width=2, dash="dash"), hovertemplate="%{y:,.0f} ₺"))
        fig.add_trace(go.Scatter(x=x, y=p50, name="Medyan" + (" (kaynaklarla)" if kaynakli else ""),
                                 line=dict(color=C["blue"], width=3), hovertemplate="<b>%{y:,.0f} ₺</b>"))
        fig.add_hline(y=0, line_dash="dash", line_color="rgba(248,113,113,0.55)", line_width=1)
        if tampon > 0:
            fig.add_hline(y=tampon, line_dash="dot", line_color="rgba(251,191,36,0.55)", line_width=1,
                          annotation_text=f"Tampon {tl_kisa(tampon)}", annotation_position="top left",
                          annotation_font=dict(size=10, color=C["amber"]))
        # Kötü senaryonun eksiye düştüğü dönemleri (ardışık gün blokları) boya
        negatif = np.r_[False, p5 < 0, False]
        sinirlar = np.flatnonzero(np.diff(negatif.astype(int)))
        for b0, b1 in zip(sinirlar[::2], sinirlar[1::2]):
            fig.add_vrect(x0=x[b0], x1=x[b1 - 1], line_width=0, layer="below", fillcolor="rgba(248,113,113,0.08)")
        if ilk_risk is not None:
            fig.add_annotation(x=x[ilk_risk], y=p5[ilk_risk], text=f"<b>{tarih_str(ilk_risk)}</b> · kötü senaryoda eksi",
                               showarrow=True, arrowhead=0, arrowcolor=C["amber"], ax=70, ay=38,
                               font=dict(color="#111827", size=11), bgcolor=C["amber"], borderpad=5)
        ortak_layout(fig, 420, hovermode="x unified",
                     legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0,
                                 font=dict(size=11, color=C["muted"]), bgcolor="rgba(0,0,0,0)"))
        fig.update_xaxes(tickformat="%d.%m", hoverformat="%d.%m.%Y")
        fig.update_layout(margin=dict(t=36, b=10, l=10, r=10))
        st.plotly_chart(fig, width="stretch", config=PLOT_CFG)

with sag:
    with st.container(key="kart_halka"):
        kart_baslik("Temerrüt Olasılığı", "En az bir gün eksi bakiye görülen senaryo oranı"
                    + (" (kaynaklar kullanıldıktan sonra)" if kaynakli else ""))
        halka = go.Figure(go.Pie(
            values=[max(temerrut, 0.001), max(100 - temerrut, 0.001)], hole=0.80, sort=False,
            direction="clockwise", rotation=90, textinfo="none", hoverinfo="skip",
            marker=dict(colors=[risk_renk, "rgba(148,163,184,0.12)"], line=dict(width=0))))
        halka.add_annotation(text=f"<b>{yuzde(temerrut)}</b>", x=0.5, y=0.56, showarrow=False,
                             font=dict(size=34, color=C["text"], family=FONT))
        halka.add_annotation(text=risk_etiket.upper(), x=0.5, y=0.36, showarrow=False,
                             font=dict(size=11, color=risk_renk, family=FONT))
        ortak_layout(halka, 210, showlegend=False)
        st.plotly_chart(halka, width="stretch", config=PLOT_CFG)
        satirlar = [("Kaynaksız temerrüt olasılığı", yuzde(temerrut_ham)),
                    ("Kötü senaryoda kapanmayan açık", f"{tl_kisa(kalan_acik)} ₺")]
        if kaynakli:
            satirlar += [("Ortalama limit faizi maliyeti", f"{tl_kisa(faiz)} ₺"),
                         ("Dönem sonu açık kredi (medyan)", f"{tl_kisa(acik_kredi)} ₺")]
        st.markdown("<div class='mini'>" + "".join(f"<span>{a}</span><span>{b}</span>" for a, b in satirlar)
                    + "</div>", unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ============================================================
# Satır 2: Nakit köprüsü + Finansman planı
# ============================================================
sol, sag = st.columns([1, 1.15], gap="medium")
with sol:
    with st.container(key="kart_kopru"):
        kart_baslik("Nakit Köprüsü", "Başlangıçtan dönem sonuna · senaryo ortalaması")
        etiket, deger = ["Başlangıç"], [s.baslangic_nakdi]
        for k in AKIS_KATEGORILERI + [KAT_KUR]:
            tutar = float(s.kategori[k].sum())
            if abs(tutar) >= 1:
                etiket.append(k)
                deger.append(tutar)
        if kaynakli:
            for k, ad in [(KAT_LIMIT, "Limit (net)"), (KAT_AKSIYON, "Aksiyonlar"), (KAT_LIMIT_FAIZ, "Limit faizi")]:
                tutar = float(s.kategori[k].sum())
                if abs(tutar) >= 1:
                    etiket.append(ad)
                    deger.append(tutar)
        son = float(B[:, -1].mean())
        etiket.append("Dönem Sonu")
        deger.append(son)
        kopru = go.Figure(go.Waterfall(
            x=etiket, y=deger, measure=["absolute"] + ["relative"] * (len(deger) - 2) + ["total"],
            text=[tl_kisa(d) for d in deger], textposition="outside", textfont=dict(size=10, color="#CBD5E1"),
            connector=dict(line=dict(color="rgba(148,163,184,0.3)", width=1)),
            increasing=dict(marker=dict(color=C["green"])), decreasing=dict(marker=dict(color=C["red"])),
            totals=dict(marker=dict(color=C["blue"])),
            hovertemplate="%{x}: <b>%{y:,.0f} ₺</b><extra></extra>"))
        ortak_layout(kopru, 420, showlegend=False)
        kopru.update_xaxes(tickangle=-30, tickfont=dict(size=10))
        kopru.update_yaxes(range=[min(0, min(np.cumsum(deger[:-1]))) * 1.15,
                                  max(np.cumsum(deger[:-1]).max(), son) * 1.18])
        st.plotly_chart(kopru, width="stretch", config=PLOT_CFG)

with sag:
    with st.container(key="kart_plan"):
        kart_baslik("Finansman Planı", "Model kaynakları bu sırayla kullanır: önce en ucuz limit, sonra öncelik sırasına göre aksiyonlar")
        if not len(rapor):
            st.markdown("<div class='bos'>Excel'de kredi limiti veya yönetim aksiyonu tanımlanmamış "
                        "(6_Kredi_Limitleri, 7_Yonetim_Aksiyonlari).</div>", unsafe_allow_html=True)
        else:
            satir_html = []
            for _, r in rapor.iterrows():
                olas = r["Kullanılma Olasılığı"] if kaynakli else 0
                renk = C["red"] if olas >= 60 else (C["amber"] if olas >= 20 else C["green"])
                ilk = tarih_str(r["İlk Kullanım Günü"]) if kaynakli and pd.notna(r["İlk Kullanım Günü"]) else "—"
                satir_html.append(
                    f"<tr><td><div class='ad'><span class='grup'>{r['Grup']}</span>{r['Kaynak']}</div>"
                    f"<div class='kosul'>{r['Koşul']}</div></td>"
                    f"<td class='sag'>{tl_kisa(r['Kapasite'])}</td>"
                    f"<td><div style='display:flex;align-items:center;gap:8px'><div class='bar'>"
                    f"<i style='width:{olas:.0f}%;background:{renk}'></i></div>{yuzde(olas)}</div></td>"
                    f"<td class='sag'>{ilk}</td></tr>")
            st.markdown("<table class='fp'><tr><th>Kaynak</th><th class='sag'>Kapasite</th>"
                        "<th>Kullanılma olasılığı</th><th class='sag'>İlk kullanım</th></tr>"
                        + "".join(satir_html) + "</table>", unsafe_allow_html=True)
            if not kaynakli:
                st.caption("Kaynak kullanımı ⚙️ Varsayımlar menüsünden kapatılmış.")
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ============================================================
# Satır 3: Haftalık akış
# ============================================================
with st.container(key="kart_haftalik"):
    kart_baslik("Haftalık Nakit Akışı", "Kategori bazında senaryo ortalaması · çizgi: haftalık net akış")
    hafta = np.arange(gun) // 7
    hafta_bas = [x[i * 7] for i in range(hafta.max() + 1)]
    hf = go.Figure()
    net_hafta = np.zeros(len(hafta_bas))
    for k in AKIS_KATEGORILERI:
        h = np.bincount(hafta, weights=s.kategori[k], minlength=len(hafta_bas))
        net_hafta += h
        if np.abs(h).sum() >= 1:
            hf.add_trace(go.Bar(x=hafta_bas, y=h, name=k, marker=dict(color=KATEGORI_RENK[k], line=dict(width=0)),
                                hovertemplate=k + ": %{y:,.0f} ₺<extra></extra>"))
    hf.add_trace(go.Scatter(x=hafta_bas, y=net_hafta, name="Net", mode="lines+markers",
                            line=dict(color="#F8FAFC", width=2), marker=dict(size=5),
                            hovertemplate="<b>Net: %{y:,.0f} ₺</b><extra></extra>"))
    ortak_layout(hf, 300, barmode="relative", bargap=0.3, hovermode="x unified",
                 legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0,
                             font=dict(size=11, color=C["muted"]), bgcolor="rgba(0,0,0,0)"))
    hf.update_xaxes(tickformat="%d.%m", hoverformat="Hafta: %d.%m.%Y")
    hf.update_layout(margin=dict(t=36, b=10, l=10, r=10))
    st.plotly_chart(hf, width="stretch", config=PLOT_CFG)

# ============================================================
# Veri kontrolleri
# ============================================================
st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
ikon = {"hata": "⛔", "uyari": "⚠️", "bilgi": "ℹ️"}
with st.expander(f"Veri kontrolleri — {hata_say} hata · {uyari_say} uyarı · "
                 f"{sum(b.seviye == 'bilgi' for b in bulgular)} bilgi", expanded=bool(hata_say)):
    if not bulgular:
        st.markdown("Tüm sayfalar sorunsuz okundu.")
    sira = {"hata": 0, "uyari": 1, "bilgi": 2}
    for b in sorted(bulgular, key=lambda b: sira[b.seviye]):
        st.markdown(f"{ikon[b.seviye]} **{b.sayfa}** — {b.mesaj}")
    ozet = " · ".join(f"{ad.split('_', 1)[1].replace('_', ' ')}: {len(df)}" for ad, df in v.tablolar.items())
    st.caption(f"Okunan satırlar — {ozet}")
