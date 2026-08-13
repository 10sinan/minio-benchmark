"""
ui/theme.py — Apple Human Interface Guidelines (HIG) Teması.

Streamlit uygulamasına Apple'ın HIG ilkelerine dayanan:
  - SF Pro tipografisi
  - Buzlu cam (Frosted Glass / Vibrancy) panel efekti
  - Squircle köşe geometrisi
  - Apple System Color paleti
  - iOS/macOS tarzı Segmented Control sekmeler
  - Plotly grafik teması (Apple Dark mode estetiği)
"""

import plotly.graph_objects as go
import streamlit as st

# ─── Apple System Renk Paleti ─────────────────────────────────────────────────

RENKLER = {
    # Arka Planlar
    "bg_ana":          "#000000",
    "bg_panel":        "rgba(28, 28, 30, 0.75)",
    "bg_panel_solid":  "#1C1C1E",
    "bg_input":        "rgba(44, 44, 46, 0.8)",
    "bg_hover":        "rgba(58, 58, 60, 0.6)",

    # Kenarlıklar
    "kenar":           "rgba(255, 255, 255, 0.10)",
    "kenar_belirgin":  "rgba(255, 255, 255, 0.18)",

    # Metin
    "metin":           "#FFFFFF",
    "metin_ikincil":   "rgba(235, 235, 245, 0.6)",
    "metin_ucuncul":   "rgba(235, 235, 245, 0.3)",

    # Apple System Colors (Dark Mode)
    "mavi":    "#0A84FF",   # System Blue  — Download, Ağ Alınan
    "yesil":   "#30D158",   # System Green — Başarılı, Ağ Gönderilen
    "turuncu": "#FF9F0C",   # System Orange— Upload, CPU
    "mor":     "#BF5AF2",   # System Purple— RAM, Multipart
    "kirmizi": "#FF453A",   # System Red   — Hata, Delete
    "sari":    "#FFD60A",   # System Yellow— Metadata, Latency
    "camgobegi":"#64D2FF",  # System Teal  — Ağ

    # Ayraçlar & gölgeler
    "separator":    "rgba(84, 84, 88, 0.65)",
    "golge":        "rgba(0, 0, 0, 0.5)",
}

# Grafiklerde sıralı kullanılacak renk listesi
GRAFIK_RENKLERI = [
    RENKLER["mavi"],
    RENKLER["yesil"],
    RENKLER["turuncu"],
    RENKLER["mor"],
    RENKLER["kirmizi"],
    RENKLER["sari"],
    RENKLER["camgobegi"],
]


# ─── CSS Enjeksiyonu ──────────────────────────────────────────────────────────

def inject_apple_hig_css() -> None:
    """
    Streamlit'e Apple HIG tabanlı koyu tema CSS'ini enjekte eder.
    ui.py'de her render döngüsünün başında çağrılmalıdır.
    """
    st.markdown(
        f"""
        <style>
        /* ── SF Pro & Apple Tipografisi ──────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"] {{
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
                         "SF Pro Text", "Helvetica Neue", Inter, sans-serif !important;
            background-color: {RENKLER["bg_ana"]} !important;
            color: {RENKLER["metin"]} !important;
            -webkit-font-smoothing: antialiased;
        }}
        .stApp {{
            background: radial-gradient(
                ellipse at top,
                rgba(10, 10, 20, 1) 0%,
                {RENKLER["bg_ana"]} 70%
            ) !important;
        }}

        /* ── Başlıklar (Large Titles) ────────────────────── */
        h1 {{
            font-size: 34px !important;
            font-weight: 700 !important;
            letter-spacing: -0.5px !important;
            color: {RENKLER["metin"]} !important;
            padding-bottom: 4px;
        }}
        h2, h3 {{
            font-weight: 600 !important;
            letter-spacing: -0.3px !important;
            color: {RENKLER["metin"]} !important;
        }}
        h4, h5 {{
            font-weight: 500 !important;
            color: {RENKLER["metin_ikincil"]} !important;
        }}

        /* ── Buzlu Cam Metrik Kartları (Stat Panels) ─────── */
        [data-testid="stMetric"] {{
            background: {RENKLER["bg_panel"]} !important;
            backdrop-filter: blur(20px) saturate(180%) !important;
            -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
            border: 1px solid {RENKLER["kenar"]} !important;
            border-radius: 16px !important;
            padding: 20px 18px !important;
            box-shadow:
                0 0 0 0.5px {RENKLER["kenar_belirgin"]},
                0 8px 32px {RENKLER["golge"]},
                inset 0 1px 0 rgba(255,255,255,0.08) !important;
            transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        }}
        [data-testid="stMetric"]:hover {{
            transform: translateY(-1px) !important;
            box-shadow:
                0 0 0 0.5px {RENKLER["kenar_belirgin"]},
                0 12px 40px {RENKLER["golge"]},
                inset 0 1px 0 rgba(255,255,255,0.1) !important;
        }}
        [data-testid="stMetricLabel"] {{
            font-size: 11px !important;
            font-weight: 500 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.6px !important;
            color: {RENKLER["metin_ikincil"]} !important;
        }}
        [data-testid="stMetricValue"] {{
            font-size: 30px !important;
            font-weight: 700 !important;
            letter-spacing: -0.5px !important;
            color: {RENKLER["metin"]} !important;
        }}

        /* ── Buzlu Cam Paneller ───────────────────────────── */
        [data-testid="stContainer"] > div,
        div[data-testid="column"] > div[data-testid="stVerticalBlock"] > div[class*="stContainer"] {{
            background: {RENKLER["bg_panel"]} !important;
            backdrop-filter: blur(20px) saturate(180%) !important;
            -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
            border: 1px solid {RENKLER["kenar"]} !important;
            border-radius: 16px !important;
            box-shadow: 0 4px 24px {RENKLER["golge"]},
                        inset 0 1px 0 rgba(255,255,255,0.06) !important;
        }}

        /* ── Expander ────────────────────────────────────── */
        [data-testid="stExpander"] {{
            background: {RENKLER["bg_input"]} !important;
            backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
            border: 1px solid {RENKLER["kenar"]} !important;
            border-radius: 12px !important;
        }}
        [data-testid="stExpander"] summary {{
            color: {RENKLER["metin"]} !important;
            font-weight: 500 !important;
            font-size: 15px !important;
        }}

        /* ── Segmented Control Sekmeler (iOS Tarzı) ──────── */
        [data-testid="stTabs"] [data-baseweb="tab-list"] {{
            background: rgba(44, 44, 46, 0.8) !important;
            backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
            border-radius: 12px !important;
            padding: 3px !important;
            border: 1px solid {RENKLER["kenar"]} !important;
            gap: 2px;
        }}
        [data-testid="stTabs"] [data-baseweb="tab"] {{
            color: {RENKLER["metin_ikincil"]} !important;
            background: transparent !important;
            border-radius: 9px !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            padding: 6px 16px !important;
            border: none !important;
            transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
        }}
        [data-testid="stTabs"] [aria-selected="true"] {{
            color: {RENKLER["metin"]} !important;
            background: rgba(58, 58, 60, 0.9) !important;
            backdrop-filter: blur(8px) !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.4),
                        inset 0 0.5px 0 rgba(255,255,255,0.15) !important;
        }}

        /* ── Input Alanları ──────────────────────────────── */
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        textarea {{
            background: {RENKLER["bg_input"]} !important;
            backdrop-filter: blur(8px) !important;
            border: 1px solid {RENKLER["kenar"]} !important;
            border-radius: 10px !important;
            color: {RENKLER["metin"]} !important;
            font-size: 15px !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }}
        [data-testid="stTextInput"] input:focus,
        [data-testid="stNumberInput"] input:focus {{
            border-color: {RENKLER["mavi"]} !important;
            box-shadow: 0 0 0 3px rgba(10, 132, 255, 0.25) !important;
        }}
        [data-testid="stSelectbox"] [data-baseweb="select"] {{
            background: {RENKLER["bg_input"]} !important;
            border: 1px solid {RENKLER["kenar"]} !important;
            border-radius: 10px !important;
        }}
        label[data-testid="stWidgetLabel"] p {{
            color: {RENKLER["metin_ikincil"]} !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            letter-spacing: 0.1px !important;
        }}

        /* ── Butonlar (iOS tarzı) ─────────────────────── */
        [data-testid="stButton"] > button {{
            background: {RENKLER["bg_input"]} !important;
            backdrop-filter: blur(8px) !important;
            border: 1px solid {RENKLER["kenar"]} !important;
            border-radius: 10px !important;
            color: {RENKLER["mavi"]} !important;
            font-size: 15px !important;
            font-weight: 500 !important;
            padding: 8px 18px !important;
            transition: all 0.15s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
        }}
        [data-testid="stButton"] > button:hover {{
            background: rgba(10, 132, 255, 0.12) !important;
            border-color: rgba(10, 132, 255, 0.4) !important;
            transform: scale(1.01) !important;
        }}
        [data-testid="stButton"] > button:active {{
            transform: scale(0.98) !important;
        }}
        [data-testid="stButton"] > button[kind="primary"] {{
            background: {RENKLER["mavi"]} !important;
            border: none !important;
            color: #FFFFFF !important;
            box-shadow: 0 4px 16px rgba(10, 132, 255, 0.4) !important;
        }}
        [data-testid="stButton"] > button[kind="primary"]:hover {{
            background: #3A9EFF !important;
            box-shadow: 0 6px 20px rgba(10, 132, 255, 0.5) !important;
            transform: scale(1.02) translateY(-1px) !important;
        }}

        /* ── Bilgi / Uyarı / Hata Kutuları ──────────────── */
        [data-testid="stAlert"] {{
            border-radius: 12px !important;
            backdrop-filter: blur(8px) !important;
        }}
        [data-testid="stAlert"][kind="info"],
        div[data-baseweb="notification"][kind="info"] {{
            background: rgba(10, 132, 255, 0.08) !important;
            border: 1px solid rgba(10, 132, 255, 0.2) !important;
        }}
        [data-testid="stAlert"][kind="success"] {{
            background: rgba(48, 209, 88, 0.08) !important;
            border: 1px solid rgba(48, 209, 88, 0.2) !important;
        }}
        [data-testid="stAlert"][kind="error"] {{
            background: rgba(255, 69, 58, 0.08) !important;
            border: 1px solid rgba(255, 69, 58, 0.2) !important;
        }}
        [data-testid="stAlert"][kind="warning"] {{
            background: rgba(255, 159, 12, 0.08) !important;
            border: 1px solid rgba(255, 159, 12, 0.2) !important;
        }}

        /* ── Tablo / Dataframe ───────────────────────────── */
        [data-testid="stDataFrame"] {{
            border: 1px solid {RENKLER["kenar"]} !important;
            border-radius: 12px !important;
            overflow: hidden !important;
        }}

        /* ── Radio / Checkbox ────────────────────────────── */
        [data-testid="stRadio"] label p,
        [data-testid="stCheckbox"] label p {{
            color: {RENKLER["metin"]} !important;
            font-size: 15px !important;
        }}

        /* ── Slider ──────────────────────────────────────── */
        [data-testid="stSlider"] {{
            accent-color: {RENKLER["mavi"]} !important;
        }}

        /* ── Divider ─────────────────────────────────────── */
        hr {{
            border: none !important;
            border-top: 0.5px solid {RENKLER["separator"]} !important;
            margin: 20px 0 !important;
        }}

        /* ── Küçük Yazılar ───────────────────────────────── */
        [data-testid="stCaptionContainer"] p, small {{
            color: {RENKLER["metin_ikincil"]} !important;
            font-size: 12px !important;
        }}

        /* ── Sidebar ─────────────────────────────────────── */
        [data-testid="stSidebar"] {{
            background: rgba(18, 18, 20, 0.95) !important;
            backdrop-filter: blur(20px) !important;
            border-right: 0.5px solid {RENKLER["separator"]} !important;
            padding-top: 0 !important;
        }}
        [data-testid="stSidebar"] > div:first-child {{
            padding-top: 1rem !important;
        }}
        [data-testid="stSidebarContent"] {{
            padding: 0.75rem 1rem !important;
        }}

        /* ── Kompakt Density ─────────────────────────────── */
        /* Streamlit'in devasa üst boşluğunu kaldır */
        .stMainBlockContainer, .block-container {{
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }}
        /* Metrik kartlarını sıkıştır */
        [data-testid="stMetric"] {{
            padding: 12px 14px !important;
            border-radius: 12px !important;
        }}
        [data-testid="stMetricValue"] {{
            font-size: 22px !important;
        }}
        [data-testid="stMetricLabel"] {{
            font-size: 10px !important;
        }}
        /* Eleman arası dikey boşluklar */
        .element-container {{
            margin-bottom: 0.4rem !important;
        }}
        /* Tab listesi kompakt */
        [data-testid="stTabs"] [data-baseweb="tab-list"] {{
            margin-bottom: 0.5rem !important;
        }}
        /* Başlık alanını küçült */
        h2 {{
            margin-top: 0 !important;
            margin-bottom: 0.5rem !important;
            font-size: 22px !important;
        }}
        /* Divider daha ince boşluk */
        hr {{
            margin: 10px 0 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ─── Plotly Apple HIG Tema Motoru ────────────────────────────────────────────

def apply_apple_hig_theme(fig: go.Figure, *, area_fill: bool = False) -> go.Figure:
    """
    Bir Plotly Figure nesnesine Apple HIG Dark Mode temasını uygular.

    Parameters
    ----------
    fig       : go.Figure  — Düzenlenecek figür
    area_fill : bool       — True ise çizgi grafiklerine şeffaf alan dolgusu ekler
    """
    for i, trace in enumerate(fig.data):
        renk = GRAFIK_RENKLERI[i % len(GRAFIK_RENKLERI)]
        if getattr(trace, "type", None) == "pie":
            continue
        try:
            if hasattr(trace, "line") and trace.line is not None:
                trace.line.color = renk
                trace.line.width = 2
        except AttributeError:
            pass
        try:
            if hasattr(trace, "marker") and trace.marker is not None:
                m_color = getattr(trace.marker, "color", None)
                if isinstance(m_color, str) or m_color is None:
                    trace.marker.color = renk
        except AttributeError:
            pass
        if area_fill and hasattr(trace, "fill"):
            def hex_rgba(h, a):
                h = h.lstrip("#")
                r, g, b = (int(h[j:j+2], 16) for j in (0, 2, 4))
                return f"rgba({r},{g},{b},{a})"
            trace.fillcolor = hex_rgba(renk, 0.10)
            trace.fill = "tozeroy"

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', sans-serif",
            color=RENKLER["metin"],
            size=12,
        ),
        title_font=dict(
            color=RENKLER["metin"],
            size=15,
            family="-apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif",
        ),
        legend=dict(
            bgcolor="rgba(28, 28, 30, 0.5)",
            bordercolor=RENKLER["kenar"],
            borderwidth=1,
            font=dict(color=RENKLER["metin_ikincil"], size=11),
        ),
        xaxis=dict(
            gridcolor="rgba(84, 84, 88, 0.3)",
            linecolor=RENKLER["separator"],
            tickfont=dict(color=RENKLER["metin_ikincil"], size=11),
            title_font=dict(color=RENKLER["metin_ikincil"]),
            zeroline=False,
            showgrid=True,
        ),
        yaxis=dict(
            gridcolor="rgba(84, 84, 88, 0.3)",
            linecolor=RENKLER["separator"],
            tickfont=dict(color=RENKLER["metin_ikincil"], size=11),
            title_font=dict(color=RENKLER["metin_ikincil"]),
            zeroline=False,
            showgrid=True,
        ),
        hoverlabel=dict(
            bgcolor="rgba(28, 28, 30, 0.95)",
            bordercolor=RENKLER["kenar_belirgin"],
            font=dict(
                color=RENKLER["metin"],
                family="-apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif",
                size=13,
            ),
        ),
        margin=dict(l=8, r=8, t=40, b=8),
    )
    return fig


def apple_renk(islem_tipi: str) -> str:
    """İşlem tipine göre Apple System Color kodu döndürür."""
    harita = {
        "upload":             RENKLER["turuncu"],
        "karma_upload":       RENKLER["turuncu"],
        "download":           RENKLER["mavi"],
        "karma_download":     RENKLER["mavi"],
        "multipart_upload":   RENKLER["mor"],
        "list_objects":       RENKLER["yesil"],
        "head_object":        RENKLER["sari"],
        "karma_head":         RENKLER["sari"],
        "delete":             RENKLER["kirmizi"],
    }
    return harita.get(islem_tipi, RENKLER["metin_ikincil"])


# Eski Grafana fonksiyon adlarını geriye dönük uyumluluk için aliasla
inject_grafana_css  = inject_apple_hig_css
apply_grafana_theme = apply_apple_hig_theme
grafana_renk        = apple_renk
