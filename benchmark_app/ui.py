"""
ui.py — Streamlit arayüzü (ana modül).

Sekmeler:
  1. 🚀 Benchmark Çalıştır  — test başlatma, canlı grafikler, sonuç paneli
  2. 📊 Geçmiş Testleri Karşılaştır — CSV'den çoklu test seçimi ve kıyaslama grafikleri

Yeni özellikler:
  * Canlı Throughput ve Latency grafikleri (polling + metrics.anlık_kopyala)
  * Multipart Upload kıyaslaması, List/Head metadata paneli
  * Kullanıcı tetiklemeli Delete benchmark (Sil & Ölç butonu)
  * Karşılaştırma sekmesi: bar + line grafiklerle yan yana kıyaslama
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
import generator
import history
import metrics
import reporter
import s3_utils

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# ──────────────────────────────────────────────────────────────────────────────
# Thread hedef fonksiyonu — session_state'e doğrudan erişmez
# ──────────────────────────────────────────────────────────────────────────────

def _benchmark_calistir(ayarlar, endpoint, access_key, secret_key, bucket_name, test_prefix, iptal_kontrol, output_dict):
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
        output_dict["prefix"] = test_prefix
    except Exception as e:
        logging.exception("Benchmark çalışırken hata: %s", e)
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
        "benchmark_hata": None,
        "benchmark_thread": None,
        "thread_output": {},
        "son_prefix": None,
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
    """Polling döngüsünde çağrılır; anlık metrik kopyasından grafikler çizer."""
    anlık = metrics.anlık_kopyala()
    if not anlık:
        placeholder.info("⏳ Henüz veri yok, bekleniyor…")
        return

    df = pd.DataFrame(anlık)
    df["zaman"] = pd.to_datetime(df["zaman"], unit="s")
    df["latency_ms"] = df["sure"] * 1000

    col1, col2 = placeholder.columns(2)

    # ── Throughput (MB/s) — yalnızca boyutlu işlemler ──────────────────────
    boyutlu = df[df["boyut_byte"].notna()].copy()
    if not boyutlu.empty:
        boyutlu["throughput_mb_s"] = (boyutlu["boyut_byte"] / (1024 * 1024)) / boyutlu["sure"].replace(0, float("nan"))
        boyutlu["zaman_str"] = boyutlu["zaman"].dt.strftime("%H:%M:%S")
        fig_tp = px.line(
            boyutlu,
            x="zaman_str",
            y="throughput_mb_s",
            color="islem_tipi",
            markers=True,
            title="Canlı Throughput (MB/s)",
            labels={"zaman_str": "Zaman", "throughput_mb_s": "MB/s", "islem_tipi": "İşlem"},
            color_discrete_map={
                "upload": "#4F8EF7",
                "download": "#22D3A5",
                "multipart_upload": "#F7A24F",
            },
        )
        fig_tp.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=35, b=0),
            legend=dict(orientation="h", y=-0.25),
        )
        col1.plotly_chart(fig_tp, width="stretch")
    else:
        col1.info("Throughput verisi bekleniyor…")

    # ── Latency (ms) — tüm işlem tipleri ───────────────────────────────────
    df["zaman_str"] = df["zaman"].dt.strftime("%H:%M:%S")
    fig_lat = px.scatter(
        df,
        x="zaman_str",
        y="latency_ms",
        color="islem_tipi",
        title="⏱ Canlı Latency (ms)",
        labels={"zaman_str": "Zaman", "latency_ms": "ms", "islem_tipi": "İşlem"},
    )
    fig_lat.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=35, b=0),
        legend=dict(orientation="h", y=-0.25),
    )
    col2.plotly_chart(fig_lat, width="stretch")


# ──────────────────────────────────────────────────────────────────────────────
# Benchmark sonuç paneli
# ──────────────────────────────────────────────────────────────────────────────

def _sonuc_paneli(df, ozet, upload_df, download_df, secilen_profil, ozel_ayarlar_kullan, settings, bucket_name, endpoint, access_key, secret_key):
    thresholds = settings["profiles"][secilen_profil]["thresholds"]
    durum = reporter.durum_degerlendir(ozet, thresholds)
    sozel = reporter.sozel_ozet(ozet, durum)

    # ── Özet metrikler ───────────────────────────────────────────────────────
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
- **Gecikme (P95):** < {thresholds["latency_iyi_sn"]} sn → İyi · {thresholds["latency_iyi_sn"]}-{thresholds["latency_orta_sn"]} sn → Orta · > {thresholds["latency_orta_sn"]} sn → Yavaş
- **Başarı oranı:** %100 → Mükemmel · %95-99.9 → İyi · <%95 → Dikkat gerekiyor
- **Throughput:** > {thresholds["throughput_iyi_mb_s"]} MB/s → İyi · {thresholds["throughput_orta_mb_s"]}-{thresholds["throughput_iyi_mb_s"]} MB/s → Orta · < {thresholds["throughput_orta_mb_s"]} MB/s → Yavaş
"""
        )

    # ── Throughput Karşılaştırma Grafiği ────────────────────────────────────
    st.subheader("Throughput Karşılaştırması")
    throughput_data = {
        "Upload (PutObject)": ozet.get("upload_throughput_mb_s", 0),
        "Download (GetObject)": ozet.get("download_throughput_mb_s", 0),
        "Multipart Upload": ozet.get("multipart_upload_throughput_mb_s", 0),
    }
    throughput_data = {k: v for k, v in throughput_data.items() if v > 0}
    if throughput_data:
        fig_bar = go.Figure(
            go.Bar(
                x=list(throughput_data.keys()),
                y=list(throughput_data.values()),
                marker_color=["#4F8EF7", "#22D3A5", "#F7A24F"][: len(throughput_data)],
                text=[f"{v:.2f}" for v in throughput_data.values()],
                textposition="outside",
            )
        )
        fig_bar.update_layout(
            yaxis_title="MB/s",
            height=300,
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_bar, width="stretch")

    # ── Metadata & Delete Paneli ─────────────────────────────────────────────
    st.subheader("Metadata Performansı")
    meta1, meta2 = st.columns(2)
    lo = ozet.get("list_objects_ops_per_sec", 0)
    ho = ozet.get("head_object_ops_per_sec", 0)
    meta1.metric("ListObjectsV2", f"{lo:.2f} ops/sn" if lo else "—")
    meta2.metric("HeadObject", f"{ho:.2f} ops/sn" if ho else "—")

    # ── Delete Benchmark (kullanıcı tetiklemeli) ─────────────────────────────
    st.subheader("Delete Benchmark (İsteğe Bağlı)")
    prefix = st.session_state.get("son_prefix")
    if not prefix:
        st.info("Silme benchmarkı için önce bir test çalıştırın.")
    elif st.session_state.delete_calisiyor:
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
        if st.button("Sil ve Ölç", key="delete_btn"):
            st.session_state.delete_calisiyor = True
            st.session_state.delete_sonuc = None
            st.session_state.delete_hata = None
            st.session_state.delete_output = {}
            dt = threading.Thread(
                target=_delete_calistir,
                args=(endpoint, access_key, secret_key, bucket_name, prefix, st.session_state.delete_output),
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

    # ── Upload / Download Detay Tabloları ────────────────────────────────────
    st.subheader("Detay Tabloları")
    col_up, col_dn = st.columns(2)
    with col_up:
        st.caption("**Upload**")
        st.dataframe(upload_df, width="stretch")
    with col_dn:
        st.caption("**Download**")
        st.dataframe(download_df, width="stretch")

    # Multipart tablosu (varsa)
    if not df.empty and "islem_tipi" in df.columns:
        mp_df = df[df["islem_tipi"] == "multipart_upload"].copy()
        if not mp_df.empty:
            st.caption("**Multipart Upload (kıyaslama)**")
            if "boyut_byte" in mp_df.columns:
                mp_df["boyut_mb"] = mp_df["boyut_byte"] / (1024 * 1024)
                mp_df = mp_df.drop(columns=["boyut_byte"])
            st.dataframe(mp_df, width="stretch")


# ──────────────────────────────────────────────────────────────────────────────
# Karşılaştırma sekmesi
# ──────────────────────────────────────────────────────────────────────────────

def _karsilastirma_sekmesi():
    st.header("Geçmiş Testleri Karşılaştır")
    gecmis_df = history.gecmisi_oku()

    if gecmis_df is None or gecmis_df.empty:
        st.info("Henüz kaydedilmiş test yok. Önce bir benchmark çalıştırın.")
        return

    # Seçim etiketi: tarih + profil + bucket
    gecmis_df["etiket"] = (
        gecmis_df["tarih"].astype(str)
        + " | "
        + gecmis_df["profil"].astype(str)
        + " | "
        + gecmis_df["bucket"].astype(str)
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

    # ── Throughput Karşılaştırması ───────────────────────────────────────────
    st.subheader("Throughput Karşılaştırması (MB/s)")
    throughput_cols = {
        "Upload (PutObject)": "upload_throughput_mb_s",
        "Download (GetObject)": "download_throughput_mb_s",
        "Multipart Upload": "multipart_upload_throughput_mb_s",
    }
    _grouped_bar(secili, secili_label, throughput_cols, "MB/s")

    # ── Gecikme Karşılaştırması ──────────────────────────────────────────────
    st.subheader("⏱ Gecikme Karşılaştırması (sn)")
    latency_cols = {
        "Ortalama": "ortalama_sure",
        "P95": "p95",
        "P99": "p99",
    }
    _grouped_bar(secili, secili_label, latency_cols, "Saniye")

    # ── Metadata Ops/sn Karşılaştırması ─────────────────────────────────────
    ops_cols = {
        "ListObjects ops/sn": "list_objects_ops_per_sec",
        "HeadObject ops/sn": "head_object_ops_per_sec",
        "Delete ops/sn": "delete_ops_per_sec",
    }
    # Yalnızca en az bir seçili testin bu sütunu > 0 ise göster
    ops_cols_mevcut = {
        k: c for k, c in ops_cols.items()
        if c in secili.columns and pd.to_numeric(secili[c], errors="coerce").fillna(0).max() > 0
    }
    if ops_cols_mevcut:
        st.subheader("🔍 Metadata & Delete Operasyon Hızı (ops/sn)")
        _grouped_bar(secili, secili_label, ops_cols_mevcut, "ops/sn")

    # ── Ham veri tablosu ─────────────────────────────────────────────────────
    with st.expander("Ham veri tablosu"):
        st.dataframe(secili.drop(columns=["etiket"], errors="ignore"), width="stretch")


def _grouped_bar(secili: pd.DataFrame, labels: list, col_map: dict, y_label: str):
    """Seçili testler için gruplu bar grafiği çizer."""
    fig = go.Figure()
    renkler = px.colors.qualitative.Set2

    for col_label, col_name in col_map.items():
        if col_name not in secili.columns:
            continue
        vals = pd.to_numeric(secili[col_name], errors="coerce").fillna(0).tolist()
        fig.add_trace(
            go.Bar(
                name=col_label,
                x=labels,
                y=vals,
                text=[f"{v:.3f}" for v in vals],
                textposition="outside",
            )
        )

    fig.update_layout(
        barmode="group",
        yaxis_title=y_label,
        height=380,
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

    st.set_page_config(page_title="MinIO Benchmark Aracı", layout="wide")
    st.title("S3 Benchmark Aracı")

    # Config
    try:
        with open("config.yaml", "r") as f:
            settings = yaml.safe_load(f)
    except Exception as e:
        st.error(f"config.yaml dosyası okunamadı: {e}")
        return

    # ── Sekmeler ─────────────────────────────────────────────────────────────
    tab_benchmark, tab_karsilastir = st.tabs(["Benchmark Çalıştır", "Geçmiş Testleri Karşılaştır"])

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
        endpoint = st.text_input("Endpoint URL", placeholder="Örnek: http://192.168.1.10:9000", key="endpoint")
        access_key = st.text_input("Access Key", key="access_key")
        secret_key = st.text_input("Secret Key", type="password", key="secret_key")
        bucket_name = st.text_input("Bucket adı", value=settings.get("bucket_name", ""), key="bucket_name")

    with kolon_ayarlar:
        st.subheader("Test Ayarları")
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
                    st.write("Hiç test klasörü bulunamadı.")
                else:
                    for idx, p in enumerate(prefixes):
                        col_isim, col_buton = st.columns([3, 1])
                        col_isim.write(p)
                        if col_buton.button("Sil", key=f"del_{p}_{idx}"):
                            deleted = s3_utils.delete_prefix(bucket_name, p, endpoint, access_key, secret_key)
                            if deleted:
                                st.success(f"{p} silindi")
                                st.rerun()
                            else:
                                st.error(f"{p} silinemedi")
            except Exception as e:
                logging.exception("Prefix listeleme/silme hatası: %s", e)
                st.error(f"S3 İşlem Hatası: {e}")

    st.divider()

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
                st.session_state.benchmark_hata = None
                st.session_state.thread_output = {}
                st.session_state.son_prefix = test_prefix
                st.session_state.delete_sonuc = None
                st.session_state.delete_hata = None

                iptal_event_obj = st.session_state.iptal_event
                thread = threading.Thread(
                    target=_benchmark_calistir,
                    args=(ayarlar, endpoint, access_key, secret_key, bucket_name,
                          test_prefix, iptal_event_obj.is_set, st.session_state.thread_output),
                    daemon=True,
                )
                st.session_state.benchmark_thread = thread
                thread.start()
                st.rerun()

    # ── Test Devam Ederken — Canlı Grafikler ─────────────────────────────────
    if st.session_state.test_calisiyor:
        thread = st.session_state.benchmark_thread
        durum_str = metrics.get_status()
        st.info(f"⚙️ **{durum_str}**")

        live_placeholder = st.empty()
        _canli_grafikleri_ciz(live_placeholder)

        if thread and thread.is_alive():
            time.sleep(1.5)
            st.rerun()
        else:
            # Thread bitti
            st.session_state.test_calisiyor = False
            output = st.session_state.thread_output
            if "hata" in output:
                st.session_state.benchmark_hata = output["hata"]
            elif "sonuc" in output:
                st.session_state.benchmark_sonuc = output["sonuc"]
            st.rerun()

    # ── Hata Gösterimi ────────────────────────────────────────────────────────
    if st.session_state.benchmark_hata:
        st.error(f"Benchmark sırasında bir hata oluştu: {st.session_state.benchmark_hata}")

    # ── Sonuç Paneli ─────────────────────────────────────────────────────────
    elif st.session_state.benchmark_sonuc is not None:
        df, ozet, upload_df, download_df = st.session_state.benchmark_sonuc

        if st.session_state.iptal_event.is_set():
            st.warning("Benchmark iptal edildi, o ana kadarki sonuçlar gösteriliyor.")
        else:
            st.success("✅ Benchmark tamamlandı!")

        # Geçmişe kaydet
        history.kaydet(
            profil_adi=secilen_profil if not ozel_ayarlar_kullan else "özel",
            bucket_name=bucket_name,
            ozet=ozet,
        )

        with st.container():
            _sonuc_paneli(
                df, ozet, upload_df, download_df,
                secilen_profil, ozel_ayarlar_kullan, settings,
                bucket_name, endpoint, access_key, secret_key,
            )

    # ── Geçmiş Testler Özet Tablosu ──────────────────────────────────────────
    st.divider()
    st.subheader("📜 Geçmiş Testler (Özet)")
    gecmis_df = history.gecmisi_oku()
    if gecmis_df is not None:
        st.dataframe(gecmis_df, width="stretch")
    else:
        st.write("Henüz kaydedilmiş test yok.")


if __name__ == "__main__":
    render()