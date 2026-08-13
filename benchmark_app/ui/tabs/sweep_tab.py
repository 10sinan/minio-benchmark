"""
ui/tabs/sweep_tab.py — Eşzamanlılık (Concurrency) Taraması Sonuçları.
"""
import pandas as pd
import streamlit as st
import plotly.express as px
from ui.theme import apply_apple_hig_theme, RENKLER

def render_sweep_tab(sweep_df: pd.DataFrame) -> None:
    """Sweep analiz sekmesini çizer."""
    st.markdown("### Concurrency Sweep Analizi")

    if sweep_df is None or sweep_df.empty:
        st.info("Henüz sweep testi verisi yok. Sol menüden Sweep testini çalıştırarak kapasite analizi yapabilirsiniz.")
        return

    st.markdown("Farklı thread sayılarının performansa etkisini inceleyin.")

    # Çizgi grafikler için sekmeler (Throughput ve Latency)
    tab1, tab2 = st.tabs(["Throughput (MB/s)", "Latency (P95 ms)"])

    if "concurrency" in sweep_df.columns:
        sweep_df = sweep_df.sort_values(by="concurrency")

        with tab1:
            if "toplam_throughput_mb_s" in sweep_df.columns:
                fig1 = px.line(
                    sweep_df, x="concurrency", y="toplam_throughput_mb_s",
                    markers=True, title="Concurrency vs Throughput",
                    labels={"concurrency": "İşçi Sayısı (Concurrency)", "toplam_throughput_mb_s": "Toplam Hız (MB/s)"}
                )
                fig1.update_traces(line_color=RENKLER["mavi"])
                st.plotly_chart(apply_apple_hig_theme(fig1), use_container_width=True)
            else:
                st.warning("Throughput verisi bulunamadı.")

        with tab2:
            if "p95" in sweep_df.columns:
                fig2 = px.line(
                    sweep_df, x="concurrency", y="p95",
                    markers=True, title="Concurrency vs P95 Latency",
                    labels={"concurrency": "İşçi Sayısı (Concurrency)", "p95": "P95 Gecikme (sn)"}
                )
                fig2.update_traces(line_color=RENKLER["turuncu"])
                st.plotly_chart(apply_apple_hig_theme(fig2), use_container_width=True)
            else:
                st.warning("Latency verisi bulunamadı.")
    else:
        st.error("Sweep verisinde 'concurrency' sütunu bulunamadı.")

    # Detaylı tablo
    st.markdown("#### Detaylı Tablo")
    st.dataframe(sweep_df, use_container_width=True)
