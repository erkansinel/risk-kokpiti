"""Renk paleti, CSS ve ortak grafik ayarları."""

C = {
    "bg": "#0B1120",
    "card": "#131C2E",
    "card_hi": "#18233A",
    "line": "rgba(148,163,184,0.14)",
    "text": "#F1F5F9",
    "muted": "#8B9AB2",
    "blue": "#38BDF8",
    "green": "#34D399",
    "red": "#F87171",
    "amber": "#FBBF24",
    "violet": "#A78BFA",
    "slate": "#64748B",
}
FONT = "Plus Jakarta Sans, Segoe UI, sans-serif"

KATEGORI_RENK = {
    "Müşteri Tahsilatı": "#34D399",
    "Yeni Satış": "#2DD4BF",
    "Tedarikçi Ödemesi": "#F87171",
    "Sabit Gider": "#FB923C",
    "Kredi / Leasing": "#F472B6",
    "Diğer Çıkış": "#C084FC",
}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, .stApp, [class*="css"], button, input, textarea, label {{
    font-family: 'Plus Jakarta Sans', 'Segoe UI', sans-serif !important;
    -webkit-font-smoothing: antialiased;
}}
.stApp {{
    background:
        radial-gradient(1200px 500px at 15% -10%, rgba(56,189,248,0.08), transparent 60%),
        radial-gradient(900px 400px at 100% 0%, rgba(52,211,153,0.05), transparent 60%),
        {C['bg']} !important;
}}

/* Sol bar / sidebar: tüm Streamlit sürümlerindeki tüm test-id'ler */
section[data-testid="stSidebar"], div[data-testid="stSidebar"], [data-testid="stSidebarNav"],
[data-testid="stSidebarCollapsedControl"], [data-testid="stSidebarCollapseButton"],
[data-testid="stExpandSidebarButton"], [data-testid="collapsedControl"] {{
    display: none !important; width: 0 !important;
}}
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], #MainMenu, footer {{ display: none !important; }}
.block-container, [data-testid="stMainBlockContainer"] {{
    padding: 1.25rem 2rem 2rem 2rem !important; max-width: 100% !important;
}}

/* Kartlar: yalnızca key verilen container'lar */
.st-key-kontrol, [class*="st-key-kart"] {{
    background: linear-gradient(180deg, {C['card_hi']} 0%, {C['card']} 100%);
    border: 1px solid {C['line']} !important; border-radius: 16px;
    box-shadow: 0 1px 0 rgba(255,255,255,0.04) inset, 0 10px 30px rgba(0,0,0,0.35);
}}
.st-key-kontrol {{ padding: 14px 22px 8px 22px; }}
[class*="st-key-kart"] {{ padding: 16px 18px 8px 18px; }}

[data-testid="stWidgetLabel"] p {{
    font-size: 0.72rem !important; font-weight: 600 !important;
    color: {C['muted']} !important; text-transform: uppercase; letter-spacing: .6px;
}}
[data-testid="stFileUploaderDropzone"] {{
    background: rgba(15,23,42,0.55) !important; border: 1px dashed rgba(148,163,184,0.3) !important;
    border-radius: 10px !important; padding: 4px 10px !important;
}}
.stButton button[kind="primary"] {{
    background: linear-gradient(135deg, #0EA5E9 0%, #2563EB 100%) !important;
    border: 0 !important; border-radius: 10px !important; font-weight: 700 !important;
    height: 42px; box-shadow: 0 6px 18px rgba(37,99,235,0.35);
}}
.stButton button[kind="secondary"], .stDownloadButton button, [data-testid="stPopover"] button {{
    border-radius: 10px !important; height: 42px; background: rgba(15,23,42,0.6) !important;
    border: 1px solid rgba(148,163,184,0.25) !important; font-weight: 600 !important;
}}
[data-testid="stExpander"] details {{
    background: {C['card']}; border: 1px solid {C['line']} !important; border-radius: 14px;
}}

/* KPI */
.kpi {{
    position: relative; overflow: hidden;
    background: linear-gradient(180deg, {C['card_hi']} 0%, {C['card']} 100%);
    border: 1px solid {C['line']}; border-radius: 16px; padding: 18px 20px; height: 132px;
    display: flex; flex-direction: column; justify-content: space-between;
    box-shadow: 0 10px 30px rgba(0,0,0,0.30);
}}
.kpi::before {{ content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--accent); }}
.kpi-t {{ font-size: .72rem; font-weight: 600; color: {C['muted']}; text-transform: uppercase; letter-spacing: .7px; }}
.kpi-v {{ font-size: 1.85rem; font-weight: 800; color: {C['text']}; letter-spacing: -.8px; line-height: 1;
          font-variant-numeric: tabular-nums; }}
.kpi-v small {{ font-size: .9rem; font-weight: 600; color: {C['muted']}; margin-left: 5px; letter-spacing: 0; }}
.pill {{ display:inline-flex; align-items:center; gap:6px; width:fit-content; max-width:100%; padding: 3px 10px;
         border-radius: 999px; font-size: .74rem; font-weight: 600; font-variant-numeric: tabular-nums;
         white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.pill-red   {{ background: rgba(248,113,113,.12); color: #FCA5A5; border: 1px solid rgba(248,113,113,.30); }}
.pill-green {{ background: rgba(52,211,153,.12);  color: #6EE7B7; border: 1px solid rgba(52,211,153,.30); }}
.pill-blue  {{ background: rgba(56,189,248,.12);  color: #7DD3FC; border: 1px solid rgba(56,189,248,.30); }}
.pill-amber {{ background: rgba(251,191,36,.12);  color: #FCD34D; border: 1px solid rgba(251,191,36,.30); }}

.kart-baslik {{ font-size: .95rem; font-weight: 700; color: {C['text']}; }}
.kart-alt    {{ font-size: .76rem; color: {C['muted']}; margin-top: 2px; }}

/* Banner */
.banner {{
    border-radius: 16px; padding: 18px 22px; margin: 16px 0 16px 0;
    display: grid; grid-template-columns: auto 1fr; gap: 18px; align-items: center;
    border: 1px solid var(--bd); background: linear-gradient(90deg, var(--bg1) 0%, {C['card']} 70%);
}}
.banner .ikon {{ width: 44px; height: 44px; border-radius: 12px; display: grid; place-items: center;
                 font-size: 1.3rem; background: var(--ic); }}
.banner .b1 {{ font-size: .78rem; font-weight: 800; letter-spacing: .8px; color: var(--tc); }}
.banner .b2 {{ font-size: .95rem; color: {C['text']}; margin-top: 4px; line-height: 1.55; }}
.banner .b2 b {{ color: #fff; }}
.banner ol {{ margin: 6px 0 0 0; padding-left: 20px; }}
.banner li {{ margin: 2px 0; }}

/* Halka kartı mini istatistikler */
.mini {{ display: grid; grid-template-columns: 1fr auto; gap: 7px 12px; font-size: .82rem; margin: 2px 4px 8px 4px; }}
.mini span:nth-child(odd) {{ color: {C['muted']}; }}
.mini span:nth-child(even) {{ color: {C['text']}; font-weight: 700; text-align: right; font-variant-numeric: tabular-nums; }}

/* Finansman planı tablosu */
.fp {{ width: 100%; border-collapse: collapse; font-size: .82rem; margin-top: 10px; border: 0 !important; }}
.fp tr, .fp td, .fp th {{ border-left: 0 !important; border-right: 0 !important; border-top: 0 !important;
                         background: transparent !important; }}
.fp th {{ text-align: left; color: {C['muted']}; font-weight: 600; font-size: .68rem; text-transform: uppercase;
          letter-spacing: .6px; padding: 6px 8px; border-bottom: 1px solid {C['line']} !important; }}
.fp td {{ padding: 9px 8px; border-bottom: 1px solid rgba(148,163,184,0.07) !important; color: {C['text']};
          font-variant-numeric: tabular-nums; vertical-align: middle; }}
.fp td.sag, .fp th.sag {{ text-align: right; }}
.fp .ad {{ font-weight: 700; }}
.fp .kosul {{ color: {C['muted']}; font-size: .72rem; margin-top: 2px; }}
.fp .grup {{ display: inline-block; font-size: .66rem; font-weight: 700; padding: 1px 7px; border-radius: 6px;
             background: rgba(148,163,184,.12); color: #CBD5E1; margin-right: 6px; }}
.bar {{ position: relative; height: 6px; border-radius: 4px; background: rgba(148,163,184,.14); width: 110px; }}
.bar i {{ position: absolute; left: 0; top: 0; bottom: 0; border-radius: 4px; }}
.bos {{ color: {C['muted']}; font-size: .85rem; padding: 18px 4px; }}
</style>
"""
