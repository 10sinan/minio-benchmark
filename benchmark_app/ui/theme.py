"""
ui/theme.py — Grafana Tarzı Koyu Dashboard Teması.

Streamlit custom CSS enjeksiyonu ve Plotly grafik teması.
Tüm grafiklere uygulanabilir ve bağımsız olarak import edilebilir.
"""

import plotly.graph_objects as go
import streamlit as st

# ─── Grafana Renk Paleti ─────────────────────────────────────────────────────

RENKLER = {
    "bg_ana": "#0B0C10",
    "bg_panel": "#181B1F",
    "bg_panel_alt": "#22252B",
    "kenar": "#2C3235",
    "metin": "#D8D9DA",
    "metin_ikincil": "#8E8E93",
    "mavi": "#5794F2",       # Download, Ağ Alınan
    "yesil": "#73BF69",      # Başarılı, Ağ Gönderilen
    "turuncu": "#FF780A",    # Upload, CPU
    "mor": "#B877D9",        # RAM, HeadObject
    "kirmizi": "#F2495C",    # Hata, Delete
    "sari": "#FADE2A",       # Uyarı, Latency
    "acik_mavi": "#37872D",
}

# Grafik çizgilerine atanacak sıralı renk listesi
GRAFIK_RENKLERI = [
    RENKLER["mavi"],
    RENKLER["yesil"],
    RENKLER["turuncu"],
    RENKLER["mor"],
    RENKLER["kirmizi"],
    RENKLER["sari"],
]


# ─── CSS Enjeksiyonu ─────────────────────────────────────────────────────────

def inject_grafana_css() -> None:
    """
    Streamlit'e Grafana tarzı koyu tema CSS'ini enjekte eder.
    ui.py'de her render döngüsünün başında çağrılmalıdır.
    """
    st.markdown(
        f"""
        <style>
        /* ── Google Fonts ─────────────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        /* ── Genel Arka Plan & Font ──────────────────────────── */
        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif !important;
            background-color: {RENKLER["bg_ana"]} !important;
            color: {RENKLER["metin"]} !important;
        }}
        .stApp {{
            background-color: {RENKLER["bg_ana"]} !important;
        }}

        /* ── Başlık Stilleri ─────────────────────────────────── */
        h1, h2, h3, h4, h5 {{
            color: {RENKLER["metin"]} !important;
            font-weight: 600 !important;
            letter-spacing: -0.3px;
        }}
        h1 {{
            border-bottom: 2px solid {RENKLER["turuncu"]};
            padding-bottom: 8px;
            margin-bottom: 24px;
        }}

        /* ── Metrik Kartları (Grafana Stat Panel) ────────────── */
        [data-testid="stMetric"] {{
            background: {RENKLER["bg_panel"]} !important;
            border: 1px solid {RENKLER["kenar"]} !important;
            border-top: 3px solid {RENKLER["mavi"]} !important;
            border-radius: 6px !important;
            padding: 16px !important;
        }}
        [data-testid="stMetric"]:nth-child(2) {{
            border-top-color: {RENKLER["yesil"]} !important;
        }}
        [data-testid="stMetric"]:nth-child(3) {{
            border-top-color: {RENKLER["kirmizi"]} !important;
        }}
        [data-testid="stMetric"]:nth-child(4) {{
            border-top-color: {RENKLER["turuncu"]} !important;
        }}
        [data-testid="stMetricLabel"] {{
            color: {RENKLER["metin_ikincil"]} !important;
            font-size: 12px !important;
            text-transform: uppercase !important;
            letter-spacing: 0.8px !important;
        }}
        [data-testid="stMetricValue"] {{
            color: {RENKLER["metin"]} !important;
            font-size: 28px !important;
            font-weight: 700 !important;
        }}

        /* ── Konteyner & Expander ────────────────────────────── */
        [data-testid="stContainer"], .stContainer {{
            background: {RENKLER["bg_panel"]} !important;
            border: 1px solid {RENKLER["kenar"]} !important;
            border-radius: 6px !important;
        }}
        [data-testid="stExpander"] {{
            background: {RENKLER["bg_panel_alt"]} !important;
            border: 1px solid {RENKLER["kenar"]} !important;
            border-radius: 6px !important;
        }}
        [data-testid="stExpander"] summary {{
            color: {RENKLER["metin"]} !important;
            font-weight: 500 !important;
        }}

        /* ── Sekmeler (Tabs) ─────────────────────────────────── */
        [data-testid="stTabs"] [data-baseweb="tab-list"] {{
            background: {RENKLER["bg_panel"]} !important;
            border-bottom: 1px solid {RENKLER["kenar"]} !important;
            gap: 4px;
        }}
        [data-testid="stTabs"] [data-baseweb="tab"] {{
            color: {RENKLER["metin_ikincil"]} !important;
            background: transparent !important;
            border-bottom: 2px solid transparent !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            padding: 8px 16px !important;
        }}
        [data-testid="stTabs"] [aria-selected="true"] {{
            color: {RENKLER["metin"]} !important;
            border-bottom: 2px solid {RENKLER["turuncu"]} !important;
            background: transparent !important;
        }}

        /* ── Input Alanları ──────────────────────────────────── */
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stSelectbox"] [data-baseweb="select"],
        textarea {{
            background: {RENKLER["bg_panel_alt"]} !important;
            border: 1px solid {RENKLER["kenar"]} !important;
            border-radius: 4px !important;
            color: {RENKLER["metin"]} !important;
        }}
        [data-testid="stTextInput"] input:focus,
        [data-testid="stNumberInput"] input:focus {{
            border-color: {RENKLER["mavi"]} !important;
            box-shadow: 0 0 0 2px rgba(87, 148, 242, 0.2) !important;
        }}
        label[data-testid="stWidgetLabel"] p {{
            color: {RENKLER["metin_ikincil"]} !important;
            font-size: 13px !important;
        }}

        /* ── Butonlar ────────────────────────────────────────── */
        [data-testid="stButton"] > button {{
            background: {RENKLER["bg_panel_alt"]} !important;
            border: 1px solid {RENKLER["kenar"]} !important;
            color: {RENKLER["metin"]} !important;
            border-radius: 4px !important;
            font-weight: 500 !important;
            font-size: 13px !important;
            transition: all 0.15s ease !important;
        }}
        [data-testid="stButton"] > button:hover {{
            border-color: {RENKLER["mavi"]} !important;
            color: {RENKLER["mavi"]} !important;
            background: rgba(87, 148, 242, 0.08) !important;
        }}
        [data-testid="stButton"] > button[kind="primary"] {{
            background: {RENKLER["turuncu"]} !important;
            border-color: {RENKLER["turuncu"]} !important;
            color: #fff !important;
        }}
        [data-testid="stButton"] > button[kind="primary"]:hover {{
            background: #e06d00 !important;
            border-color: #e06d00 !important;
            color: #fff !important;
        }}

        /* ── Bilgi / Uyarı / Hata Kutuları ─────────────────── */
        [data-testid="stAlert"] {{
            border-radius: 4px !important;
            border-left-width: 4px !important;
        }}
        [data-testid="stAlert"][data-baseweb="notification"][kind="info"] {{
            background: rgba(87, 148, 242, 0.1) !important;
            border-left-color: {RENKLER["mavi"]} !important;
        }}
        [data-testid="stAlert"][kind="success"] {{
            background: rgba(115, 191, 105, 0.1) !important;
            border-left-color: {RENKLER["yesil"]} !important;
        }}
        [data-testid="stAlert"][kind="error"] {{
            background: rgba(242, 73, 92, 0.1) !important;
            border-left-color: {RENKLER["kirmizi"]} !important;
        }}
        [data-testid="stAlert"][kind="warning"] {{
            background: rgba(250, 222, 42, 0.08) !important;
            border-left-color: {RENKLER["sari"]} !important;
        }}

        /* ── Tablo / Dataframe ───────────────────────────────── */
        [data-testid="stDataFrame"] {{
            border: 1px solid {RENKLER["kenar"]} !important;
            border-radius: 6px !important;
        }}
        .dvn-scroller, .dvn-row {{
            background: {RENKLER["bg_panel"]} !important;
        }}

        /* ── Radio & Checkbox ────────────────────────────────── */
        [data-testid="stRadio"] label p,
        [data-testid="stCheckbox"] label p {{
            color: {RENKLER["metin"]} !important;
        }}

        /* ── Slider ──────────────────────────────────────────── */
        [data-testid="stSlider"] [data-baseweb="slider"] {{
            color: {RENKLER["turuncu"]} !important;
        }}

        /* ── Yan Çubuk (Divider) ─────────────────────────────── */
        hr {{
            border-color: {RENKLER["kenar"]} !important;
            margin: 20px 0 !important;
        }}

        /* ── Caption / Küçük Yazılar ─────────────────────────── */
        [data-testid="stCaptionContainer"] p,
        small, .caption {{
            color: {RENKLER["metin_ikincil"]} !important;
        }}

        /* ── Plotly Grafik Arka Planı ────────────────────────── */
        .js-plotly-plot .plotly .bg {{
            fill: {RENKLER["bg_panel"]} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ─── Plotly Tema Motoru ──────────────────────────────────────────────────────

def apply_grafana_theme(fig: go.Figure, *, area_fill: bool = False) -> go.Figure:
    """
    Bir Plotly Figure nesnesine Grafana Dark temasını uygular.

    Parameters
    ----------
    fig        : go.Figure  — Düzenlenecek figür
    area_fill  : bool       — True ise çizgi grafiklerine alan dolgusu (tonexty) ekler
    """
    # Renk döngüsü
    for i, trace in enumerate(fig.data):
        renk = GRAFIK_RENKLERI[i % len(GRAFIK_RENKLERI)]
        if hasattr(trace, "line") and trace.line is not None:
            trace.line.color = renk
            trace.line.width = 2
        if hasattr(trace, "marker") and trace.marker is not None:
            trace.marker.color = renk
        if hasattr(trace, "fillcolor") and area_fill:
            # RGBA fill (saydamlıklı neon parlama)
            hex_to_rgb = lambda h: tuple(int(h.lstrip("#")[j:j+2], 16) for j in (0, 2, 4))
            r, g, b = hex_to_rgb(renk)
            trace.fillcolor = f"rgba({r},{g},{b},0.12)"
            trace.fill = "tozeroy"

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=RENKLER["bg_panel"],
        font=dict(family="Inter, sans-serif", color=RENKLER["metin"], size=12),
        title_font=dict(color=RENKLER["metin"], size=14, family="Inter, sans-serif"),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=RENKLER["kenar"],
            borderwidth=1,
            font=dict(color=RENKLER["metin_ikincil"], size=11),
        ),
        xaxis=dict(
            gridcolor=RENKLER["kenar"],
            linecolor=RENKLER["kenar"],
            tickfont=dict(color=RENKLER["metin_ikincil"], size=11),
            title_font=dict(color=RENKLER["metin_ikincil"]),
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor=RENKLER["kenar"],
            linecolor=RENKLER["kenar"],
            tickfont=dict(color=RENKLER["metin_ikincil"], size=11),
            title_font=dict(color=RENKLER["metin_ikincil"]),
            zeroline=False,
        ),
        hoverlabel=dict(
            bgcolor=RENKLER["bg_panel_alt"],
            bordercolor=RENKLER["kenar"],
            font=dict(color=RENKLER["metin"], family="Inter, sans-serif", size=12),
        ),
        margin=dict(l=8, r=8, t=36, b=8),
    )
    return fig


def grafana_renk(islem_tipi: str) -> str:
    """İşlem tipine göre Grafana renk kodu döndürür."""
    harita = {
        "upload": RENKLER["turuncu"],
        "karma_upload": RENKLER["turuncu"],
        "download": RENKLER["mavi"],
        "karma_download": RENKLER["mavi"],
        "multipart_upload": RENKLER["mor"],
        "list_objects": RENKLER["yesil"],
        "head_object": RENKLER["sari"],
        "karma_head": RENKLER["sari"],
        "delete": RENKLER["kirmizi"],
    }
    return harita.get(islem_tipi, RENKLER["metin_ikincil"])
