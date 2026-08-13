"""
ui/tabs/details_tab.py — Detaylar Sekmesi.

Test tamamlandıktan sonra gösterilir:
  - Standart Benchmark sonuçları
  - Karma İş Yükü sonuçları
  - KPI barı, Sil ve Ölç paneli, Geçmişe kaydetme
"""

import threading

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analytics import reporter, history
from core import deleter
from ui.components import kpi_bari, delete_paneli
from ui.theme import apply_apple_hig_theme, RENKLER


def render(ctx: dict) -> None:
    """Detaylar Sekmesi içeriğini çizer."""
    endpoint    = ctx["endpoint"]
    access_key  = ctx["access_key"]
    secret_key  = ctx["secret_key"]
    bucket_name = ctx["bucket_name"]
    test_adi    = ctx["test_adi"]
    secilen_profil      = ctx["secilen_profil"]
    ozel_ayarlar_kullan = ctx["ozel_ayarlar_kullan"]
    auto_temizle        = ctx.get("auto_temizle", False)
    settings    = ctx["settings"]

    if st.session_state.benchmark_hata:
        st.error(f"Hata: {st.session_state.benchmark_hata}")

    elif st.session_state.benchmark_sonuc is not None:
        df, ozet, upload_df, download_df = st.session_state.benchmark_sonuc
        st.success("Benchmark Tamamlandı")
        kpi_bari(ozet)
        _standart_detay(df, ozet, upload_df, download_df, secilen_profil, settings)
        history.kaydet(
            profil_adi=secilen_profil if not ozel_ayarlar_kullan else "özel",
            bucket_name=bucket_name, ozet=ozet, test_adi=test_adi,
        )
        st.divider()
        if auto_temizle and st.session_state.son_prefix:
            _auto_temizle(endpoint, access_key, secret_key, bucket_name,
                          st.session_state.son_prefix)
        else:
            delete_paneli(st.session_state.son_prefix, endpoint, access_key,
                          secret_key, bucket_name)

    elif st.session_state.karma_sonuc is not None:
        df, ozet, res_data = st.session_state.karma_sonuc
        st.success("Karma Benchmark Tamamlandı")
        kpi_bari(ozet)
        _karma_detay(df, ozet, res_data)
        history.kaydet(
            profil_adi=f"karma_{secilen_profil}" if not ozel_ayarlar_kullan else "karma_özel",
            bucket_name=bucket_name, ozet=ozet, test_adi=test_adi,
        )
        st.divider()
        if auto_temizle and st.session_state.son_prefix:
            _auto_temizle(endpoint, access_key, secret_key, bucket_name,
                          st.session_state.son_prefix)
        else:
            delete_paneli(st.session_state.son_prefix, endpoint, access_key,
                          secret_key, bucket_name)

    else:
        st.info("Test tamamlandıktan sonra detaylar burada görünecek.")


def _auto_temizle(endpoint, access_key, secret_key, bucket_name, prefix):
    """Test bitiminde bucket prefix'ini otomatik siler."""
    bayrak_key = f"auto_temizlendi_{prefix}"
    if st.session_state.get(bayrak_key):
        st.success(f"`{prefix}` otomatik temizlendi.")
        return

    with st.spinner(f"`{prefix}` otomatik temizleniyor…"):
        try:
            sonuc = deleter.benchmark_delete(
                bucket_name=bucket_name,
                endpoint_url=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                prefix=prefix,
            )
            st.session_state[bayrak_key] = True
            silinen = sonuc.get("basarili_silinen", 0)
            st.success(f"`{prefix}` temizlendi — {silinen} nesne silindi.")
        except Exception as e:
            st.error(f"Otomatik temizlik başarısız: {e}")


def _standart_detay(df, ozet, upload_df, download_df, secilen_profil, settings):
    """Standart benchmark sonuç panelini çizer."""
    thresholds = settings["profiles"][secilen_profil]["thresholds"]
    durum  = reporter.durum_degerlendir(ozet, thresholds)
    sozel  = reporter.sozel_ozet(ozet, durum)

    tp_data = {
        "Upload":    ozet.get("upload_throughput_mb_s", 0),
        "Download":  ozet.get("download_throughput_mb_s", 0),
        "Multipart": ozet.get("multipart_upload_throughput_mb_s", 0),
    }
    tp_data = {k: v for k, v in tp_data.items() if v > 0}
    if tp_data:
        renkler_list = [RENKLER["turuncu"], RENKLER["mavi"], RENKLER["mor"]][:len(tp_data)]
        fig_bar = go.Figure(go.Bar(
            x=list(tp_data.keys()), y=list(tp_data.values()),
            marker_color=renkler_list,
            text=[f"{v:.2f}" for v in tp_data.values()], textposition="outside",
        ))
        fig_bar.update_layout(yaxis_title="MB/s", height=250, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(apply_apple_hig_theme(fig_bar), width="stretch")

    c1, c2 = st.columns(2)
    lo = ozet.get("list_objects_ops_per_sec", 0)
    ho = ozet.get("head_object_ops_per_sec", 0)
    c1.metric("ListObjectsV2", f"{lo:.2f} ops/sn" if lo else "—")
    c2.metric("HeadObject",    f"{ho:.2f} ops/sn" if ho else "—")

    st.caption(sozel)

    with st.expander("Detay Tabloları"):
        col_u, col_d = st.columns(2)
        with col_u:
            st.caption("Upload")
            st.dataframe(upload_df, width="stretch")
        with col_d:
            st.caption("Download")
            st.dataframe(download_df, width="stretch")

        if not df.empty and "islem_tipi" in df.columns:
            mp_df = df[df["islem_tipi"] == "multipart_upload"].copy()
            if not mp_df.empty:
                st.caption("Multipart Upload")
                if "boyut_byte" in mp_df.columns:
                    mp_df["boyut_mb"] = mp_df["boyut_byte"] / (1024 * 1024)
                    mp_df = mp_df.drop(columns=["boyut_byte"])
                st.dataframe(mp_df, width="stretch")


def _karma_detay(df, ozet, resource_data):
    """Karma İş Yükü sonuç panelini çizer."""
    if not df.empty and "islem_tipi" in df.columns:
        dagilim = df["islem_tipi"].value_counts().reset_index()
        dagilim.columns = ["islem_tipi", "sayi"]

        col1, col2 = st.columns(2)

        fig_pie = px.pie(
            dagilim, names="islem_tipi", values="sayi",
            title="İşlem Dağılımı",
            color_discrete_map={
                "karma_upload":   RENKLER["turuncu"],
                "karma_download": RENKLER["mavi"],
                "karma_head":     RENKLER["sari"],
            },
        )
        fig_pie.update_layout(height=240, margin=dict(l=0, r=0, t=32, b=0))
        col1.plotly_chart(apply_apple_hig_theme(fig_pie), width="stretch")

        karma_tp = {k: v for k, v in {
            "Upload":   ozet.get("karma_upload_throughput_mb_s", 0),
            "Download": ozet.get("karma_download_throughput_mb_s", 0),
        }.items() if v > 0}
        if karma_tp:
            fig_tp = go.Figure(go.Bar(
                x=list(karma_tp.keys()), y=list(karma_tp.values()),
                marker_color=[RENKLER["turuncu"], RENKLER["mavi"]],
                text=[f"{v:.2f}" for v in karma_tp.values()], textposition="outside",
            ))
            fig_tp.update_layout(
                title="Karma Throughput (MB/s)", yaxis_title="MB/s",
                height=240, margin=dict(l=0, r=0, t=32, b=0),
            )
            col2.plotly_chart(apply_apple_hig_theme(fig_tp), width="stretch")

    kh = ozet.get("karma_head_ops_per_sec", 0)
    if kh:
        st.metric("Karma HeadObject ops/sn", f"{kh:.2f}")

    if resource_data:
        res_df = pd.DataFrame(resource_data)
        res_df["zaman_str"] = pd.to_datetime(res_df["zaman"], unit="s").dt.strftime("%H:%M:%S")

        col3, col4 = st.columns(2)

        fig_cpu = go.Figure()
        fig_cpu.add_trace(go.Scatter(x=res_df["zaman_str"], y=res_df["cpu_pct"],
                                     name="CPU %", mode="lines",
                                     line=dict(color=RENKLER["turuncu"])))
        fig_cpu.add_trace(go.Scatter(x=res_df["zaman_str"], y=res_df["ram_pct"],
                                     name="RAM %", mode="lines",
                                     line=dict(color=RENKLER["mor"])))
        fig_cpu.update_layout(title="CPU & RAM (%)", yaxis_range=[0, 100],
                              height=240, margin=dict(l=0, r=0, t=32, b=0),
                              legend=dict(orientation="h", y=-0.35))
        col3.plotly_chart(apply_apple_hig_theme(fig_cpu), width="stretch")

        fig_net = go.Figure()
        fig_net.add_trace(go.Scatter(x=res_df["zaman_str"], y=res_df["net_gonderilen_mb_s"],
                                     name="Gönderilen", mode="lines",
                                     line=dict(color=RENKLER["mavi"])))
        fig_net.add_trace(go.Scatter(x=res_df["zaman_str"], y=res_df["net_alinan_mb_s"],
                                     name="Alınan", mode="lines",
                                     line=dict(color=RENKLER["yesil"])))
        fig_net.update_layout(title="Ağ Trafiği (MB/s)", height=240,
                              margin=dict(l=0, r=0, t=32, b=0),
                              legend=dict(orientation="h", y=-0.35))
        col4.plotly_chart(apply_apple_hig_theme(fig_net), width="stretch")

    if not df.empty:
        with st.expander("Ham Veri Tablosu"):
            st.dataframe(df, width="stretch")
