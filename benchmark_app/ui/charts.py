"""
ui/charts.py — Canlı İzleme Grafik Bileşenleri.

Bu modül, Streamlit canlı dashboard'unda gösterilen
2x2 kompakt grafik grid'ini ve yardımcı bileşenleri içerir.

Grafikler:
  - 🚀 Throughput (MB/s) — Anlık işlem verisinden hesaplanır
  - ⏱ Latency (ms)      — Anlık istek süreleri scatter plot
  - 🖥 CPU & RAM (%)    — psutil kaynak izleyiciden
  - 🌐 Ağ Trafiği       — psutil ağ arayüzü trafiği
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analytics import metrics, resource_monitor
from ui.theme import apply_apple_hig_theme, RENKLER


# ──────────────────────────────────────────────────────────────────────────────
# 2x2 Kompakt Grafik Grid
# ──────────────────────────────────────────────────────────────────────────────

def grafik_paneli() -> None:
    """
    2x2 kompakt grafik grid'ini çizer.
    Canlı izleme sekmesinde polling döngüsünde çağrılır.
    """
    anlık = metrics.anlık_kopyala()
    res = resource_monitor.get_data()

    col1, col2 = st.columns(2)

    with col1:
        _throughput_grafik(anlık)

    with col2:
        _latency_grafik(anlık)

    col3, col4 = st.columns(2)

    with col3:
        _cpu_ram_grafik(res)

    with col4:
        _ag_trafigi_grafik(res)


# ──────────────────────────────────────────────────────────────────────────────
# Bireysel Grafik Çizimleri
# ──────────────────────────────────────────────────────────────────────────────

def _throughput_grafik(anlık: list) -> None:
    """Sol Üst: Anlık Throughput (MB/s) çizgi grafiği."""
    if not anlık:
        _bos_grafik("🚀 Throughput")
        return

    df = pd.DataFrame(anlık)
    df["zaman_str"] = pd.to_datetime(df["zaman"], unit="s").dt.strftime("%H:%M:%S")
    boyutlu = df[df["boyut_byte"].notna()].copy()

    if boyutlu.empty:
        st.info("Throughput verisi bekleniyor…")
        return

    boyutlu["throughput_mb_s"] = (
        boyutlu["boyut_byte"] / (1024 * 1024)
    ) / boyutlu["sure"].replace(0, float("nan"))

    fig = px.line(
        boyutlu, x="zaman_str", y="throughput_mb_s",
        color="islem_tipi", markers=True,
        labels={"zaman_str": "", "throughput_mb_s": "MB/s", "islem_tipi": ""},
        title="🚀 Throughput",
    )
    fig.update_layout(
        height=230, margin=dict(l=0, r=0, t=32, b=0),
        legend=dict(orientation="h", y=-0.35, font=dict(size=10)),
    )
    st.plotly_chart(apply_apple_hig_theme(fig, area_fill=True), width="stretch")


def _latency_grafik(anlık: list) -> None:
    """Sağ Üst: Anlık Latency (ms) scatter grafiği."""
    if not anlık:
        _bos_grafik("⏱ Latency")
        return

    df = pd.DataFrame(anlık)
    df["zaman_str"] = pd.to_datetime(df["zaman"], unit="s").dt.strftime("%H:%M:%S")
    df["latency_ms"] = df["sure"] * 1000

    fig = px.scatter(
        df, x="zaman_str", y="latency_ms", color="islem_tipi",
        labels={"zaman_str": "", "latency_ms": "ms", "islem_tipi": ""},
        title="⏱ Latency",
    )
    fig.update_layout(
        height=230, margin=dict(l=0, r=0, t=32, b=0),
        legend=dict(orientation="h", y=-0.35, font=dict(size=10)),
    )
    st.plotly_chart(apply_apple_hig_theme(fig), width="stretch")


def _cpu_ram_grafik(res: list) -> None:
    """Sol Alt: CPU & RAM (%) çizgi grafiği."""
    if not res:
        _bos_grafik("🖥 CPU & RAM")
        return

    res_df = pd.DataFrame(res)
    res_df["zaman_str"] = pd.to_datetime(res_df["zaman"], unit="s").dt.strftime("%H:%M:%S")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=res_df["zaman_str"], y=res_df["cpu_pct"],
        mode="lines", name="CPU %",
        line=dict(color=RENKLER["turuncu"], width=2),
    ))
    fig.add_trace(go.Scatter(
        x=res_df["zaman_str"], y=res_df["ram_pct"],
        mode="lines", name="RAM %",
        line=dict(color=RENKLER["mor"], width=2),
    ))
    fig.update_layout(
        title="🖥 CPU & RAM", yaxis_title="%",
        yaxis_range=[0, 100], height=230,
        margin=dict(l=0, r=0, t=32, b=0),
        legend=dict(orientation="h", y=-0.35, font=dict(size=10)),
    )
    st.plotly_chart(apply_apple_hig_theme(fig), width="stretch")


def _ag_trafigi_grafik(res: list) -> None:
    """Sağ Alt: Ağ Trafiği (MB/s) çizgi grafiği."""
    if not res:
        _bos_grafik("🌐 Ağ Trafiği")
        return

    res_df = pd.DataFrame(res)
    res_df["zaman_str"] = pd.to_datetime(res_df["zaman"], unit="s").dt.strftime("%H:%M:%S")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=res_df["zaman_str"], y=res_df["net_gonderilen_mb_s"],
        mode="lines", name="Gönderilen",
        line=dict(color=RENKLER["mavi"], width=2),
    ))
    fig.add_trace(go.Scatter(
        x=res_df["zaman_str"], y=res_df["net_alinan_mb_s"],
        mode="lines", name="Alınan",
        line=dict(color=RENKLER["yesil"], width=2),
    ))
    fig.update_layout(
        title="🌐 Ağ Trafiği", yaxis_title="MB/s",
        height=230, margin=dict(l=0, r=0, t=32, b=0),
        legend=dict(orientation="h", y=-0.35, font=dict(size=10)),
    )
    st.plotly_chart(apply_apple_hig_theme(fig), width="stretch")


def _bos_grafik(baslik: str) -> None:
    """Veri yokken boş/placeholder grafik çizer."""
    fig = go.Figure()
    fig.update_layout(title=baslik, height=230, margin=dict(l=0, r=0, t=32, b=0))
    fig.add_annotation(
        text="Veri bekleniyor…", showarrow=False,
        font=dict(color=RENKLER["metin_ikincil"], size=14),
    )
    st.plotly_chart(apply_apple_hig_theme(fig), width="stretch")
