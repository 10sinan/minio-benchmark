"""
ui/tabs/history_tab.py — 📜 Geçmiş & Karşılaştır Sekmesi.

Özellikler:
  - Kaydedilmiş tüm testlerin tablo görünümü
  - Test ismi yeniden adlandırma (rename) paneli
  - Seçili testleri Throughput / Latency / Metadata grouped bar grafiklerle karşılaştırma
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics import history
from ui.theme import apply_apple_hig_theme


# ──────────────────────────────────────────────────────────────────────────────
# Ana Render
# ──────────────────────────────────────────────────────────────────────────────

def render() -> None:
    """Geçmiş & Karşılaştır Sekmesi içeriğini çizer."""
    gecmis_df = history.gecmisi_oku()

    if gecmis_df is None or gecmis_df.empty:
        st.info("Henüz kaydedilmiş test yok.")
        return

    _rename_paneli(gecmis_df)
    _gecmis_tablosu(gecmis_df)
    _karsilastirma_paneli(gecmis_df)


# ──────────────────────────────────────────────────────────────────────────────
# Alt Bileşenler
# ──────────────────────────────────────────────────────────────────────────────

def _rename_paneli(gecmis_df: pd.DataFrame) -> None:
    """Test ismini yeniden adlandırma bileşeni."""
    with st.expander("✏️ Test İsmini Yeniden Adlandır"):
        secilecekler = {
            row["test_id"]: f"{row['test_adi']} ({row['tarih']})"
            for _, row in gecmis_df.iterrows()
        }
        secilen_id = st.selectbox(
            "Test seçin:", options=list(secilecekler.keys()),
            format_func=lambda x: secilecekler[x], key="rename_select",
        )
        mevcut_isim = (
            gecmis_df[gecmis_df["test_id"] == secilen_id]["test_adi"].values[0]
            if secilen_id else ""
        )
        yeni_isim = st.text_input("Yeni isim:", value=mevcut_isim)
        if st.button("Güncelle", key="rename_btn"):
            if history.isim_guncelle(secilen_id, yeni_isim):
                st.success("Test ismi güncellendi!")
                st.rerun()
            else:
                st.error("Güncelleme başarısız.")


def _gecmis_tablosu(gecmis_df: pd.DataFrame) -> None:
    """Kaydedilmiş testlerin tablo görünümü."""
    gosterilecek = gecmis_df.drop(columns=["test_id"], errors="ignore")
    if "test_adi" in gosterilecek.columns:
        cols = ["test_adi"] + [c for c in gosterilecek.columns if c != "test_adi"]
        gosterilecek = gosterilecek[cols]
    st.dataframe(gosterilecek, width="stretch")


def _karsilastirma_paneli(gecmis_df: pd.DataFrame) -> None:
    """Seçili testler arasında grouped bar grafik karşılaştırması."""
    st.subheader("📊 Testleri Karşılaştır")

    gecmis_df = gecmis_df.copy()
    gecmis_df["etiket"] = (
        "📌 " + gecmis_df["test_adi"].astype(str) + " (" +
        gecmis_df["tarih"].astype(str) + " | " +
        gecmis_df["profil"].astype(str) + ")"
    )
    secimler = st.multiselect(
        "Karşılaştırılacak testleri seçin (en az 2):",
        options=gecmis_df["etiket"].tolist(),
        key="karsilastirma_secim",
    )
    if len(secimler) < 2:
        st.info("Karşılaştırma için en az 2 test seçin.")
        return

    secili = gecmis_df[gecmis_df["etiket"].isin(secimler)].copy()
    secili_label = secili["etiket"].tolist()

    # Throughput & Latency yan yana
    c_tp, c_lat = st.columns(2)
    with c_tp:
        st.caption("Throughput (MB/s)")
        _grouped_bar(secili, secili_label, {
            "Upload":    "upload_throughput_mb_s",
            "Download":  "download_throughput_mb_s",
            "Multipart": "multipart_upload_throughput_mb_s",
        }, "MB/s")
    with c_lat:
        st.caption("Gecikme (sn)")
        _grouped_bar(secili, secili_label, {
            "Ort.": "ortalama_sure",
            "P95":  "p95",
            "P99":  "p99",
        }, "sn")

    # Metadata & Delete ops/sn (yalnızca veri varsa)
    ops_cols = {
        "ListObjects ops/sn": "list_objects_ops_per_sec",
        "HeadObject ops/sn":  "head_object_ops_per_sec",
        "Delete ops/sn":      "delete_ops_per_sec",
    }
    ops_mevcut = {
        k: c for k, c in ops_cols.items()
        if c in secili.columns and
           pd.to_numeric(secili[c], errors="coerce").fillna(0).max() > 0
    }
    if ops_mevcut:
        st.caption("Metadata & Delete (ops/sn)")
        _grouped_bar(secili, secili_label, ops_mevcut, "ops/sn")


def _grouped_bar(secili: pd.DataFrame, secili_label: list,
                 col_map: dict, y_label: str) -> None:
    """Verilen sütun haritasından grouped bar grafiği çizer."""
    fig = go.Figure()
    for col_label, col_name in col_map.items():
        if col_name not in secili.columns:
            continue
        vals = pd.to_numeric(secili[col_name], errors="coerce").fillna(0).tolist()
        fig.add_trace(go.Bar(
            name=col_label, x=secili_label, y=vals,
            text=[f"{v:.2f}" for v in vals], textposition="outside",
        ))
    fig.update_layout(
        barmode="group", yaxis_title=y_label, height=320,
        margin=dict(l=0, r=0, t=10, b=80),
        legend=dict(orientation="h", y=-0.35),
        xaxis=dict(tickangle=-15),
    )
    st.plotly_chart(apply_apple_hig_theme(fig), width="stretch")
