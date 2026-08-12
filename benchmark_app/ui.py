"""
ui.py — Streamlit arayüzü (ana modül).

Sekmeler:
  1. 🚀 Benchmark Çalıştır   — Standart veya Karma İş Yükü modu
  2. 📊 Geçmiş Testleri Karşılaştır

Yeni Faz 2 özellikleri:
  * Mod seçimi: Standart / Karma İş Yükü
  * Karma mod: süre + oran slider'ları
  * Canlı grafiklere CPU, RAM ve Ağ satırı (psutil)
  * Karma sonuç paneli (karma_upload / karma_download / karma_head)
"""

import logging
import threading
import time
import uuid

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yaml

import actions
import deleter
import history
import metrics
import reporter
import s3_utils
from analytics import resource_monitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# ──────────────────────────────────────────────────────────────────────────────
# Thread hedef fonksiyonları
# ──────────────────────────────────────────────────────────────────────────────

def _benchmark_calistir(
    ayarlar, endpoint, access_key, secret_key, bucket_name,
    test_prefix, iptal_kontrol, output_dict,
):
    """Standart benchmark thread'i."""
    try:
        df, ozet, upload_df, download_df = actions.run_benchmark(
            ayarlar=ayarlar,
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            bucket_name=bucket_name,
            test_prefix=test_prefix,
            iptal_kontrol=iptal_kontrol,
        )
        output_dict["sonuc"] = (df, ozet, upload_df, download_df)
        output_dict["mod"] = "standart"
    except Exception as e:
        logging.exception("Standart benchmark hatası: %s", e)
        output_dict["hata"] = str(e)


def _karma_benchmark_calistir(
    ayarlar, endpoint, access_key, secret_key, bucket_name,
    test_prefix, karma_ayarlar, iptal_kontrol, output_dict,
):
    """Karma İş Yükü benchmark thread'i."""
    try:
        df, ozet, res_data = actions.run_mixed_benchmark(
            ayarlar=ayarlar,
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            bucket_name=bucket_name,
            test_prefix=test_prefix,
            karma_ayarlar=karma_ayarlar,
            iptal_kontrol=iptal_kontrol,
        )
        output_dict["karma_sonuc"] = (df, ozet, res_data)
        output_dict["mod"] = "karma"
    except Exception as e:
        logging.exception("Karma benchmark hatası: %s", e)
        output_dict["hata"] = str(e)


def _delete_calistir(endpoint, access_key, secret_key, bucket_name, prefix, output_dict):
    try:
        sonuc = deleter.benchmark_delete(
            bucket_name=bucket_name,
            endpoint_url=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            prefix=prefix,
        )
        output_dict["delete_sonuc"] = sonuc
    except Exception as e:
        logging.exception("Delete benchmark hatası: %s", e)
        output_dict["delete_hata"] = str(e)


# ──────────────────────────────────────────────────────────────────────────────
# Session state başlatma
# ──────────────────────────────────────────────────────────────────────────────

def _init_state():
    defaults = {
        "iptal_event": threading.Event(),
        "test_calisiyor": False,
        "benchmark_sonuc": None,
        "karma_sonuc": None,
        "benchmark_hata": None,
        "benchmark_thread": None,
        "thread_output": {},
        "son_prefix": None,
        "son_mod": "standart",
        # Delete state
        "delete_calisiyor": False,
        "delete_thread": None,
        "delete_output": {},
        "delete_sonuc": None,
        "delete_hata": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ──────────────────────────────────────────────────────────────────────────────
# Canlı grafik yardımcıları
# ──────────────────────────────────────────────────────────────────────────────

def _canli_grafikleri_ciz(placeholder):
    """Polling döngüsünde çağrılır; Throughput, Latency ve Kaynak grafiklerini çizer."""
    anlık = metrics.anlık_kopyala()

    # ── Satır 1: Throughput + Latency ─────────────────────────────────────────
    with placeholder.container():
        if anlık:
            df = pd.DataFrame(anlık)
            df["zaman"] = pd.to_datetime(df["zaman"], unit="s")
            df["latency_ms"] = df["sure"] * 1000
            df["zaman_str"] = df["zaman"].dt.strftime("%H:%M:%S")

            col1, col2 = st.columns(2)

            # Throughput
            boyutlu = df[df["boyut_byte"].notna()].copy()
            if not boyutlu.empty:
                boyutlu["throughput_mb_s"] = (
                    boyutlu["boyut_byte"] / (1024 * 1024)
                ) / boyutlu["sure"].replace(0, float("nan"))
                fig_tp = px.line(
                    boyutlu,
                    x="zaman_str",
                    y="throughput_mb_s",
                    color="islem_tipi",
                    markers=True,
                    title="🚀 Canlı Throughput (MB/s)",
                    labels={"zaman_str": "Zaman", "throughput_mb_s": "MB/s", "islem_tipi": "İşlem"},
                )
                fig_tp.update_layout(height=280, margin=dict(l=0, r=0, t=35, b=0),
                                     legend=dict(orientation="h", y=-0.3))
                col1.plotly_chart(fig_tp, width="stretch")
            else:
                col1.info("Throughput verisi bekleniyor…")

            # Latency
            fig_lat = px.scatter(
                df, x="zaman_str", y="latency_ms", color="islem_tipi",
                title="⏱ Canlı Latency (ms)",
                labels={"zaman_str": "Zaman", "latency_ms": "ms", "islem_tipi": "İşlem"},
            )
            fig_lat.update_layout(height=280, margin=dict(l=0, r=0, t=35, b=0),
                                  legend=dict(orientation="h", y=-0.3))
            col2.plotly_chart(fig_lat, width="stretch")
        else:
            st.info("⏳ Henüz metrik yok, bekleniyor…")

        # ── Satır 2: CPU & Ağ (kaynak izleyici verisi) ─────────────────────
        res = resource_monitor.get_data()
        if res:
            res_df = pd.DataFrame(res)
            res_df["zaman"] = pd.to_datetime(res_df["zaman"], unit="s")
            res_df["zaman_str"] = res_df["zaman"].dt.strftime("%H:%M:%S")

            col3, col4 = st.columns(2)

            fig_cpu = go.Figure()
            fig_cpu.add_trace(go.Scatter(
                x=res_df["zaman_str"], y=res_df["cpu_pct"],
                mode="lines+markers", name="CPU %",
                line=dict(color="#F7A24F"),
            ))
            fig_cpu.add_trace(go.Scatter(
                x=res_df["zaman_str"], y=res_df["ram_pct"],
                mode="lines+markers", name="RAM %",
                line=dict(color="#A78BFA"),
            ))
            fig_cpu.update_layout(
                title="🖥 Canlı CPU & RAM (%)",
                yaxis_title="%", yaxis_range=[0, 100],
                height=250, margin=dict(l=0, r=0, t=35, b=0),
                legend=dict(orientation="h", y=-0.3),
            )
            col3.plotly_chart(fig_cpu, width="stretch")

            fig_net = go.Figure()
            fig_net.add_trace(go.Scatter(
                x=res_df["zaman_str"], y=res_df["net_gonderilen_mb_s"],
                mode="lines+markers", name="Gönderilen",
                line=dict(color="#4F8EF7"),
            ))
            fig_net.add_trace(go.Scatter(
                x=res_df["zaman_str"], y=res_df["net_alinan_mb_s"],
                mode="lines+markers", name="Alınan",
                line=dict(color="#22D3A5"),
            ))
            fig_net.update_layout(
                title="🌐 Canlı Ağ Trafiği (MB/s)",
                yaxis_title="MB/s",
                height=250, margin=dict(l=0, r=0, t=35, b=0),
                legend=dict(orientation="h", y=-0.3),
            )
            col4.plotly_chart(fig_net, width="stretch")


# ──────────────────────────────────────────────────────────────────────────────
# Standart Benchmark sonuç paneli
# ──────────────────────────────────────────────────────────────────────────────

def _sonuc_paneli(
    df, ozet, upload_df, download_df,
    secilen_profil, ozel_ayarlar_kullan, settings,
    bucket_name, endpoint, access_key, secret_key,
):
    thresholds = settings["profiles"][secilen_profil]["thresholds"]
    durum = reporter.durum_degerlendir(ozet, thresholds)
    sozel = reporter.sozel_ozet(ozet, durum)

    st.subheader("📋 Özet")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Toplam İşlem", ozet.get("toplam_dosya", 0))
    m2.metric("Başarılı", ozet.get("basarili", 0))
    m3.metric("Hatalı", ozet.get("hatali", 0))
    m4.metric("Ort. Süre", f"{ozet.get('ortalama_sure', 0):.3f} sn")

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("P95", f"{ozet.get('p95', 0):.3f} sn")
    m6.metric("P99", f"{ozet.get('p99', 0):.3f} sn")
    m7.metric("Toplam Throughput", f"{ozet.get('toplam_throughput_mb_s', 0):.2f} MB/s")
    m8.metric("Başarı Oranı", f"%{durum.get('basari_orani', 0):.1f}")

    st.caption(
        f"Gecikme: {durum.get('latency_durum', 'N/A')} | "
        f"Başarı: {durum.get('basari_durum', 'N/A')} | "
        f"Throughput: {durum.get('throughput_durum', 'N/A')}"
    )
    st.write(sozel)

    with st.expander("Değerlendirme kriterleri nedir?"):
        st.markdown(
            f"""
Bu değerlendirme, **{secilen_profil}** profiline göre yapılmıştır:
- **P95:** < {thresholds["latency_iyi_sn"]} sn → İyi · {thresholds["latency_iyi_sn"]}-{thresholds["latency_orta_sn"]} sn → Orta · > {thresholds["latency_orta_sn"]} sn → Yavaş
- **Başarı oranı:** %100 → Mükemmel · %95-99.9 → İyi · <%95 → Dikkat gerekiyor
- **Throughput:** > {thresholds["throughput_iyi_mb_s"]} MB/s → İyi · {thresholds["throughput_orta_mb_s"]}-{thresholds["throughput_iyi_mb_s"]} MB/s → Orta · < {thresholds["throughput_orta_mb_s"]} MB/s → Yavaş
"""
        )

    # Throughput Karşılaştırma Grafiği
    st.subheader("📈 Throughput Karşılaştırması")
    throughput_data = {
        "Upload": ozet.get("upload_throughput_mb_s", 0),
        "Download": ozet.get("download_throughput_mb_s", 0),
        "Multipart Upload": ozet.get("multipart_upload_throughput_mb_s", 0),
    }
    throughput_data = {k: v for k, v in throughput_data.items() if v > 0}
    if throughput_data:
        fig_bar = go.Figure(go.Bar(
            x=list(throughput_data.keys()), y=list(throughput_data.values()),
            marker_color=["#4F8EF7", "#22D3A5", "#F7A24F"][: len(throughput_data)],
            text=[f"{v:.2f}" for v in throughput_data.values()], textposition="outside",
        ))
        fig_bar.update_layout(yaxis_title="MB/s", height=300, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_bar, width="stretch")

    # Metadata Paneli
    st.subheader("🔍 Metadata Performansı")
    meta1, meta2 = st.columns(2)
    lo = ozet.get("list_objects_ops_per_sec", 0)
    ho = ozet.get("head_object_ops_per_sec", 0)
    meta1.metric("ListObjectsV2", f"{lo:.2f} ops/sn" if lo else "—")
    meta2.metric("HeadObject", f"{ho:.2f} ops/sn" if ho else "—")

    # Delete Benchmark (kullanıcı tetiklemeli)
    _delete_paneli(prefix=st.session_state.get("son_prefix"),
                   endpoint=endpoint, access_key=access_key,
                   secret_key=secret_key, bucket_name=bucket_name)

    # Detay Tabloları
    st.subheader("📂 Detay Tabloları")
    col_up, col_dn = st.columns(2)
    with col_up:
        st.caption("**Upload**")
        st.dataframe(upload_df, width="stretch")
    with col_dn:
        st.caption("**Download**")
        st.dataframe(download_df, width="stretch")

    if not df.empty and "islem_tipi" in df.columns:
        mp_df = df[df["islem_tipi"] == "multipart_upload"].copy()
        if not mp_df.empty:
            st.caption("**Multipart Upload (kıyaslama)**")
            if "boyut_byte" in mp_df.columns:
                mp_df["boyut_mb"] = mp_df["boyut_byte"] / (1024 * 1024)
                mp_df = mp_df.drop(columns=["boyut_byte"])
            st.dataframe(mp_df, width="stretch")


# ──────────────────────────────────────────────────────────────────────────────
# Karma İş Yükü sonuç paneli
# ──────────────────────────────────────────────────────────────────────────────

def _karma_sonuc_paneli(df, ozet, resource_data):
    st.subheader("📋 Karma İş Yükü Özeti")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Toplam İşlem", ozet.get("toplam_dosya", 0))
    m2.metric("Başarılı", ozet.get("basarili", 0))
    m3.metric("Hatalı", ozet.get("hatali", 0))
    m4.metric("P95 Latency", f"{ozet.get('p95', 0):.3f} sn")

    # Karma işlem dağılımı
    if not df.empty and "islem_tipi" in df.columns:
        dagilim = df["islem_tipi"].value_counts().reset_index()
        dagilim.columns = ["islem_tipi", "sayi"]
        fig_pie = px.pie(
            dagilim, names="islem_tipi", values="sayi",
            title="📊 İşlem Dağılımı",
            color_discrete_map={
                "karma_upload": "#4F8EF7",
                "karma_download": "#22D3A5",
                "karma_head": "#F7A24F",
            },
        )
        fig_pie.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0))

        # Karma throughput bar grafiği
        karma_tp = {
            "Upload": ozet.get("karma_upload_throughput_mb_s", 0),
            "Download": ozet.get("karma_download_throughput_mb_s", 0),
        }
        karma_tp = {k: v for k, v in karma_tp.items() if v > 0}

        col1, col2 = st.columns(2)
        col1.plotly_chart(fig_pie, width="stretch")

        if karma_tp:
            fig_tp = go.Figure(go.Bar(
                x=list(karma_tp.keys()), y=list(karma_tp.values()),
                marker_color=["#4F8EF7", "#22D3A5"],
                text=[f"{v:.2f}" for v in karma_tp.values()], textposition="outside",
            ))
            fig_tp.update_layout(
                title="Karma Throughput (MB/s)",
                yaxis_title="MB/s", height=300, margin=dict(l=0, r=0, t=40, b=0),
            )
            col2.plotly_chart(fig_tp, width="stretch")

    # Karma Head ops/sn
    kh = ozet.get("karma_head_ops_per_sec", 0)
    if kh:
        st.metric("Karma HeadObject ops/sn", f"{kh:.2f}")

    # Kaynak Kullanımı Grafikleri
    if resource_data:
        st.subheader("🖥 Test Boyunca Kaynak Kullanımı")
        res_df = pd.DataFrame(resource_data)
        res_df["zaman"] = pd.to_datetime(res_df["zaman"], unit="s")
        res_df["zaman_str"] = res_df["zaman"].dt.strftime("%H:%M:%S")

        col3, col4 = st.columns(2)
        fig_cpu = go.Figure()
        fig_cpu.add_trace(go.Scatter(
            x=res_df["zaman_str"], y=res_df["cpu_pct"], name="CPU %",
            mode="lines+markers", line=dict(color="#F7A24F"),
        ))
        fig_cpu.add_trace(go.Scatter(
            x=res_df["zaman_str"], y=res_df["ram_pct"], name="RAM %",
            mode="lines+markers", line=dict(color="#A78BFA"),
        ))
        fig_cpu.update_layout(
            title="CPU & RAM (%)", yaxis_title="%", yaxis_range=[0, 100],
            height=280, margin=dict(l=0, r=0, t=35, b=0),
            legend=dict(orientation="h", y=-0.3),
        )
        col3.plotly_chart(fig_cpu, width="stretch")

        fig_net = go.Figure()
        fig_net.add_trace(go.Scatter(
            x=res_df["zaman_str"], y=res_df["net_gonderilen_mb_s"],
            name="Gönderilen", mode="lines+markers", line=dict(color="#4F8EF7"),
        ))
        fig_net.add_trace(go.Scatter(
            x=res_df["zaman_str"], y=res_df["net_alinan_mb_s"],
            name="Alınan", mode="lines+markers", line=dict(color="#22D3A5"),
        ))
        fig_net.update_layout(
            title="Ağ Trafiği (MB/s)", yaxis_title="MB/s",
            height=280, margin=dict(l=0, r=0, t=35, b=0),
            legend=dict(orientation="h", y=-0.3),
        )
        col4.plotly_chart(fig_net, width="stretch")

    # Ham tablo
    if not df.empty:
        with st.expander("Ham veri tablosu"):
            st.dataframe(df, width="stretch")


# ──────────────────────────────────────────────────────────────────────────────
# Delete Paneli (paylaşımlı)
# ──────────────────────────────────────────────────────────────────────────────

def _delete_paneli(prefix, endpoint, access_key, secret_key, bucket_name):
    st.subheader("🗑️ Delete Benchmark (İsteğe Bağlı)")
    if not prefix:
        st.info("Silme benchmarkı için önce bir test çalıştırın.")
        return

    if st.session_state.delete_calisiyor:
        st.info("⏳ Delete benchmark devam ediyor…")
        dt = st.session_state.delete_thread
        if dt and dt.is_alive():
            time.sleep(0.5)
            st.rerun()
        else:
            st.session_state.delete_calisiyor = False
            dout = st.session_state.delete_output
            if "delete_hata" in dout:
                st.session_state.delete_hata = dout["delete_hata"]
            elif "delete_sonuc" in dout:
                st.session_state.delete_sonuc = dout["delete_sonuc"]
            st.rerun()
    else:
        if st.button("🗑️ Sil ve Ölç", key="delete_btn"):
            st.session_state.delete_calisiyor = True
            st.session_state.delete_sonuc = None
            st.session_state.delete_hata = None
            st.session_state.delete_output = {}
            dt = threading.Thread(
                target=_delete_calistir,
                args=(endpoint, access_key, secret_key, bucket_name, prefix,
                      st.session_state.delete_output),
                daemon=True,
            )
            st.session_state.delete_thread = dt
            dt.start()
            st.rerun()

    if st.session_state.delete_hata:
        st.error(f"Delete benchmark hatası: {st.session_state.delete_hata}")
    elif st.session_state.delete_sonuc:
        ds = st.session_state.delete_sonuc
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Toplam Nesne", ds.get("toplam_nesne", 0))
        d2.metric("Silinen", ds.get("basarili_silinen", 0))
        d3.metric("Toplam Süre", f"{ds.get('toplam_sure_sn', 0):.3f} sn")
        d4.metric("Hız", f"{ds.get('ops_per_sec', 0):.1f} ops/sn")


# ──────────────────────────────────────────────────────────────────────────────
# Karşılaştırma sekmesi
# ──────────────────────────────────────────────────────────────────────────────

def _karsilastirma_sekmesi():
    st.header("📊 Geçmiş Testleri Karşılaştır")
    gecmis_df = history.gecmisi_oku()

    if gecmis_df is None or gecmis_df.empty:
        st.info("Henüz kaydedilmiş test yok. Önce bir benchmark çalıştırın.")
        return

    gecmis_df["etiket"] = (
        "📌 " + gecmis_df["test_adi"].astype(str) + " (" +
        gecmis_df["tarih"].astype(str) + " | " +
        gecmis_df["profil"].astype(str) + " | " +
        gecmis_df["bucket"].astype(str) + ")"
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

    st.subheader("🚀 Throughput Karşılaştırması (MB/s)")
    _grouped_bar(secili, secili_label, {
        "Upload": "upload_throughput_mb_s",
        "Download": "download_throughput_mb_s",
        "Multipart Upload": "multipart_upload_throughput_mb_s",
    }, "MB/s")

    st.subheader("⏱ Gecikme Karşılaştırması (sn)")
    _grouped_bar(secili, secili_label, {
        "Ortalama": "ortalama_sure",
        "P95": "p95",
        "P99": "p99",
    }, "Saniye")

    ops_cols = {
        "ListObjects ops/sn": "list_objects_ops_per_sec",
        "HeadObject ops/sn": "head_object_ops_per_sec",
        "Delete ops/sn": "delete_ops_per_sec",
    }
    ops_mevcut = {
        k: c for k, c in ops_cols.items()
        if c in secili.columns and pd.to_numeric(secili[c], errors="coerce").fillna(0).max() > 0
    }
    if ops_mevcut:
        st.subheader("🔍 Metadata & Delete Operasyon Hızı (ops/sn)")
        _grouped_bar(secili, secili_label, ops_mevcut, "ops/sn")

    with st.expander("Ham veri tablosu"):
        st.dataframe(secili.drop(columns=["etiket"], errors="ignore"), width="stretch")


def _grouped_bar(secili, labels, col_map, y_label):
    fig = go.Figure()
    for col_label, col_name in col_map.items():
        if col_name not in secili.columns:
            continue
        vals = pd.to_numeric(secili[col_name], errors="coerce").fillna(0).tolist()
        fig.add_trace(go.Bar(
            name=col_label, x=labels, y=vals,
            text=[f"{v:.3f}" for v in vals], textposition="outside",
        ))
    fig.update_layout(
        barmode="group", yaxis_title=y_label, height=380,
        margin=dict(l=0, r=0, t=10, b=100),
        legend=dict(orientation="h", y=-0.35),
        xaxis=dict(tickangle=-20),
    )
    st.plotly_chart(fig, width="stretch")


# ──────────────────────────────────────────────────────────────────────────────
# Ana render fonksiyonu
# ──────────────────────────────────────────────────────────────────────────────

def render():
    _init_state()
    st.set_page_config(page_title="MinIO Benchmark Aracı", layout="wide", page_icon="⚡")
    st.title("⚡ MinIO / S3 Benchmark Aracı")

    try:
        with open("config.yaml", "r") as f:
            settings = yaml.safe_load(f)
    except Exception as e:
        st.error(f"config.yaml dosyası okunamadı: {e}")
        return

    tab_benchmark, tab_karsilastir = st.tabs(
        ["🚀 Benchmark Çalıştır", "📊 Geçmiş Testleri Karşılaştır"]
    )

    with tab_benchmark:
        _benchmark_sekmesi(settings)

    with tab_karsilastir:
        _karsilastirma_sekmesi()


# ──────────────────────────────────────────────────────────────────────────────
# Benchmark sekmesi
# ──────────────────────────────────────────────────────────────────────────────

def _benchmark_sekmesi(settings):
    # ── Bağlantı & Ayarlar ───────────────────────────────────────────────────
    kolon_baglanti, kolon_ayarlar, kolon_bucket = st.columns(3)

    with kolon_baglanti:
        st.subheader("Bağlantı Bilgileri")
        endpoint = st.text_input("Endpoint URL", placeholder="http://192.168.1.10:9000", key="endpoint")
        access_key = st.text_input("Access Key", key="access_key")
        secret_key = st.text_input("Secret Key", type="password", key="secret_key")
        bucket_name = st.text_input("Bucket adı", value=settings.get("bucket_name", ""), key="bucket_name")

    with kolon_ayarlar:
        st.subheader("Test Ayarları")
        test_adi = st.text_input("Test Adı / Etiketi", placeholder="Örn: NVMe-MinIO-Benchmark-1", key="test_adi_input")
        profil_isimleri = list(settings["profiles"].keys())
        secilen_profil = st.selectbox("Profil seç", profil_isimleri, key="secilen_profil")
        ozel_ayarlar_kullan = st.checkbox("Özel ayarlar kullan", key="ozel_ayarlar")

        varsayilan = settings["profiles"][secilen_profil]
        file_count = varsayilan["file_count"]
        file_size_min_mb = varsayilan["file_size_min_mb"]
        file_size_max_mb = varsayilan["file_size_max_mb"]
        concurrency = varsayilan["concurrency"]

        if ozel_ayarlar_kullan:
            file_count = st.number_input("Dosya sayısı", min_value=1, value=int(file_count), step=1)
            file_size_min_mb = st.number_input("Min boyut (MB)", min_value=0.0, value=float(file_size_min_mb), step=0.1)
            file_size_max_mb = st.number_input("Max boyut (MB)", min_value=0.0, value=float(file_size_max_mb), step=0.1)
            concurrency = st.number_input("Concurrency", min_value=1, value=int(concurrency), step=1)

    with kolon_bucket:
        st.subheader("Bucket Test Klasörleri")
        if not (bucket_name and endpoint and access_key and secret_key):
            st.info("Bağlantı bilgilerini doldurun.")
        else:
            try:
                prefixes = s3_utils.list_prefixes(bucket_name, endpoint, access_key, secret_key)
                if not prefixes:
                    st.info("📂 Hiç test klasörü bulunamadı.")
                else:
                    st.caption("Mevcut test klasörleri:")
                    for idx, p in enumerate(prefixes):
                        with st.container(border=True):
                            col_isim, col_buton = st.columns([3, 1], vertical_alignment="center")
                            col_isim.markdown(f"📁 **{p}**")
                            if col_buton.button("🗑️ Sil", key=f"del_{p}_{idx}", use_container_width=True):
                                deleted = s3_utils.delete_prefix(bucket_name, p, endpoint, access_key, secret_key)
                                if deleted:
                                    st.success(f"{p} silindi")
                                    st.rerun()
                                else:
                                    st.error(f"{p} silinemedi")
            except Exception as e:
                logging.exception("Prefix listeleme hatası: %s", e)
                st.error(f"S3 İşlem Hatası: {e}")

    st.divider()

    # ── Mod Seçimi ────────────────────────────────────────────────────────────
    secilen_mod = st.radio(
        "Benchmark Modu",
        ["📊 Standart Benchmark", "🔀 Karma İş Yükü"],
        horizontal=True,
        key="benchmark_modu",
        disabled=st.session_state.test_calisiyor,
    )
    karma_mod = secilen_mod == "🔀 Karma İş Yükü"

    # ── Karma İş Yükü Ayarları ────────────────────────────────────────────────
    karma_ayarlar = {}
    if karma_mod:
        st.markdown("#### 🔀 Karma İş Yükü Ayarları")
        ck1, ck2 = st.columns(2)
        with ck1:
            sure_sn = st.slider("Toplam Test Süresi (sn)", min_value=10, max_value=300,
                                value=60, step=10, key="karma_sure")
        with ck2:
            st.caption("İşlem Oranları (toplam 100 olmalı)")
            upload_pct = st.slider("Upload %", 0, 100, 20, 5, key="karma_upload_pct")
            download_pct = st.slider("Download %", 0, 100 - upload_pct, 70, 5, key="karma_download_pct")
            head_pct = 100 - upload_pct - download_pct
            st.info(f"HeadObject otomatik: **%{head_pct}**")

        karma_ayarlar = {
            "sure_sn": sure_sn,
            "upload_agirlik": upload_pct,
            "download_agirlik": download_pct,
            "head_agirlik": head_pct,
        }

    # ── Başlat / Durdur ──────────────────────────────────────────────────────
    buton_kol1, buton_kol2 = st.columns([1, 4])
    with buton_kol1:
        start_button = st.button("▶ Başlat", type="primary", disabled=st.session_state.test_calisiyor)
    with buton_kol2:
        if st.session_state.test_calisiyor:
            if st.button("⏹ Durdur"):
                st.session_state.iptal_event.set()
                st.warning("İptal isteği alındı, mevcut işlem tamamlanınca durdurulacak…")

    # ── Test Başlatma ─────────────────────────────────────────────────────────
    if start_button:
        if not endpoint or not access_key or not secret_key or not bucket_name:
            st.error("Lütfen tüm bağlantı bilgilerini doldurun.")
        else:
            try:
                with st.spinner("MinIO bağlantısı kontrol ediliyor…"):
                    s3_utils.baglanti_kontrolu(endpoint, access_key, secret_key, bucket_name)
            except Exception as hata:
                st.error(f"MinIO bağlantısı doğrulanamadı: {hata}")
            else:
                test_prefix = f"test_{uuid.uuid4().hex[:8]}"
                ayarlar = {
                    "file_count": int(file_count),
                    "file_size_min_mb": float(file_size_min_mb),
                    "file_size_max_mb": float(file_size_max_mb),
                    "concurrency": int(concurrency),
                }

                st.session_state.test_calisiyor = True
                st.session_state.iptal_event.clear()
                st.session_state.benchmark_sonuc = None
                st.session_state.karma_sonuc = None
                st.session_state.benchmark_hata = None
                st.session_state.thread_output = {}
                st.session_state.son_prefix = test_prefix
                st.session_state.son_mod = "karma" if karma_mod else "standart"
                st.session_state.delete_sonuc = None
                st.session_state.delete_hata = None

                iptal_fn = st.session_state.iptal_event.is_set

                if karma_mod:
                    thread = threading.Thread(
                        target=_karma_benchmark_calistir,
                        args=(ayarlar, endpoint, access_key, secret_key, bucket_name,
                              test_prefix, karma_ayarlar, iptal_fn,
                              st.session_state.thread_output),
                        daemon=True,
                    )
                else:
                    thread = threading.Thread(
                        target=_benchmark_calistir,
                        args=(ayarlar, endpoint, access_key, secret_key, bucket_name,
                              test_prefix, iptal_fn, st.session_state.thread_output),
                        daemon=True,
                    )

                st.session_state.benchmark_thread = thread
                thread.start()
                st.rerun()

    # ── Test Devam Ederken — Canlı Grafikler ─────────────────────────────────
    if st.session_state.test_calisiyor:
        thread = st.session_state.benchmark_thread
        st.info(f"⚙️ **{metrics.get_status()}**")

        live_placeholder = st.empty()
        _canli_grafikleri_ciz(live_placeholder)

        if thread and thread.is_alive():
            time.sleep(1.5)
            st.rerun()
        else:
            st.session_state.test_calisiyor = False
            output = st.session_state.thread_output
            if "hata" in output:
                st.session_state.benchmark_hata = output["hata"]
            elif "sonuc" in output:
                st.session_state.benchmark_sonuc = output["sonuc"]
            elif "karma_sonuc" in output:
                st.session_state.karma_sonuc = output["karma_sonuc"]
            st.rerun()

    # ── Hata Gösterimi ────────────────────────────────────────────────────────
    if st.session_state.benchmark_hata:
        st.error(f"Benchmark hatası: {st.session_state.benchmark_hata}")

    # ── Standart Sonuç Paneli ─────────────────────────────────────────────────
    elif st.session_state.benchmark_sonuc is not None:
        df, ozet, upload_df, download_df = st.session_state.benchmark_sonuc
        if st.session_state.iptal_event.is_set():
            st.warning("Benchmark iptal edildi.")
        else:
            st.success("✅ Benchmark tamamlandı!")
        history.kaydet(
            profil_adi=secilen_profil if not ozel_ayarlar_kullan else "özel",
            bucket_name=bucket_name, ozet=ozet, test_adi=test_adi,
        )
        with st.container():
            _sonuc_paneli(
                df, ozet, upload_df, download_df,
                secilen_profil, ozel_ayarlar_kullan, settings,
                bucket_name, endpoint, access_key, secret_key,
            )

    # ── Karma Sonuç Paneli ────────────────────────────────────────────────────
    elif st.session_state.karma_sonuc is not None:
        df, ozet, res_data = st.session_state.karma_sonuc
        if st.session_state.iptal_event.is_set():
            st.warning("Benchmark iptal edildi.")
        else:
            st.success("✅ Karma İş Yükü tamamlandı!")
        history.kaydet(
            profil_adi=f"karma_{secilen_profil}" if not ozel_ayarlar_kullan else "karma_özel",
            bucket_name=bucket_name, ozet=ozet, test_adi=test_adi,
        )
        with st.container():
            _karma_sonuc_paneli(df, ozet, res_data)
        _delete_paneli(prefix=st.session_state.get("son_prefix"),
                       endpoint=endpoint, access_key=access_key,
                       secret_key=secret_key, bucket_name=bucket_name)

    # ── Geçmiş Testler ────────────────────────────────────────────────────────
    st.divider()
    st.subheader("📜 Geçmiş Testler (Özet)")
    gecmis_df = history.gecmisi_oku()
    if gecmis_df is not None and not gecmis_df.empty:
        # ── Yeniden Adlandırma (Rename) Alanı ──
        with st.expander("✏️ Test İsmini Yeniden Adlandır"):
            secilecekler = {row["test_id"]: f"{row['test_adi']} ({row['tarih']})" for _, row in gecmis_df.iterrows()}
            secilen_id = st.selectbox("Değiştirilecek testi seçin:", options=list(secilecekler.keys()), format_func=lambda x: secilecekler[x])
            yeni_isim = st.text_input("Yeni İsim:", value=gecmis_df[gecmis_df["test_id"] == secilen_id]["test_adi"].values[0] if secilen_id else "")
            if st.button("Güncelle"):
                if history.isim_guncelle(secilen_id, yeni_isim):
                    st.success("Test ismi güncellendi!")
                    st.rerun()
                else:
                    st.error("Güncelleme başarısız oldu.")
        
        # ── Tablo Gösterimi ──
        # test_id sütununu gizle
        gosterilecek_df = gecmis_df.drop(columns=["test_id"], errors="ignore")
        # test_adi sütununu en başa al
        if "test_adi" in gosterilecek_df.columns:
            cols = ["test_adi"] + [col for col in gosterilecek_df.columns if col != "test_adi"]
            gosterilecek_df = gosterilecek_df[cols]
        st.dataframe(gosterilecek_df, width="stretch")
    else:
        st.write("Henüz kaydedilmiş test yok.")


if __name__ == "__main__":
    render()