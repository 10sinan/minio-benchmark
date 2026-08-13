"""
ui/components.py — Paylaşılan UI Bileşenleri.
"""

import logging
import threading
import time

import streamlit as st

from core import s3_utils
from ui.state import delete_thread_fn
from ui.theme import RENKLER


def kpi_bari(ozet: dict) -> None:
    """Üst satırda 5 adet kompakt metrik kartı gösterir."""
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("İşlem",     ozet.get("toplam_dosya", "—"))
    k2.metric("Başarılı",  ozet.get("basarili", "—"))
    k3.metric("Hatalı",    ozet.get("hatali", "—"))
    k4.metric("Throughput", f"{ozet.get('toplam_throughput_mb_s', 0):.1f} MB/s")
    k5.metric("P95",        f"{ozet.get('p95', 0):.3f} sn")


def sidebar(settings: dict) -> dict:
    """Sol sidebar içeriğini oluşturur."""
    with st.sidebar:
        # ── Bağlantı ─────────────────────────────────────────────────────────
        st.markdown("### Bağlantı Ayarları")
        endpoint   = st.text_input("Endpoint URL", placeholder="http://10.0.0.1:9000", key="endpoint")
        access_key = st.text_input("Access Key", key="access_key")
        secret_key = st.text_input("Secret Key", type="password", key="secret_key")
        bucket_name = st.text_input("Bucket", value=settings.get("bucket_name", ""), key="bucket_name")

        # ── Test Ayarları ─────────────────────────────────────────────────────
        st.divider()
        st.markdown("### Test Ayarları")
        test_adi = st.text_input("Test Adı", placeholder="Örn: NVMe-Cluster-1", key="test_adi_input")
        profil_isimleri = list(settings["profiles"].keys())
        secilen_profil = st.selectbox("Profil", profil_isimleri, key="secilen_profil")
        ozel_ayarlar = st.checkbox("Özel ayarlar", key="ozel_ayarlar")

        varsayilan = settings["profiles"][secilen_profil]
        file_count       = varsayilan["file_count"]
        file_size_min_mb = varsayilan["file_size_min_mb"]
        file_size_max_mb = varsayilan["file_size_max_mb"]
        concurrency      = varsayilan["concurrency"]

        if ozel_ayarlar:
            file_count       = st.number_input("Dosya sayısı", min_value=1,  value=int(file_count),        step=1)
            file_size_min_mb = st.number_input("Min (MB)",     min_value=0.0, value=float(file_size_min_mb), step=0.1)
            file_size_max_mb = st.number_input("Max (MB)",     min_value=0.0, value=float(file_size_max_mb), step=0.1)
            concurrency      = st.number_input("Concurrency",  min_value=1,  value=int(concurrency),        step=1)

        # ── Seçenekler ────────────────────────────────────────────────────
        st.divider()
        st.markdown("### Seçenekler")
        auto_temizle = st.checkbox(
            "Test sonrası bucket'ı otomatik temizle",
            key="auto_temizle",
            help="Test tamamlanınca oluşturulan nesneler otomatik olarak silinir.",
        )
        isinma_evresi = st.checkbox(
            "Isınma Evresi (Warm-up)",
            key="isinma_evresi",
            value=True,
            help="Asıl benchmark başlamadan önce disk ve ağ bağlantılarını ısıtmak için 3 saniyelik bir ön test yapılır. Isınma verileri ana istatistiklere katılmaz.",
        )

        # ── Benchmark Modu ────────────────────────────────────────────────────
        st.divider()
        st.markdown(
            "### Benchmark Modu",
            help=(
                "Standart: Sırayla upload ve download performansını ölçer.\n\n"
                "Karma İş Yükü: Aynı anda okuma, yazma ve sorgulama eylemlerini karıştırır.\n\n"
                "Concurrency Sweep: 1-32 işçi sayılarını sırayla deneyip sunucu kapasite sınırını bulur.\n\n"
                "Değişken Boyut Matrisi: Aynı anda hem küçük (4 KB) hem büyük (100 MB) dosyaları yükler."
            ),
        )
        secilen_mod = st.radio(
            "Benchmark Modu Seçimi",
            ["Standart", "Karma İş Yükü", "Concurrency Sweep", "Değişken Boyut Matrisi"],
            captions=[
                "Sırayla standart upload ve download testi yapar.",
                "Eşzamanlı okuma, yazma ve sorgulama eylemlerini karıştırır.",
                "1 ile 32 işçi sayısını deneyerek kapasite sınırını bulur.",
                "Aynı anda hem küçük (4 KB) hem büyük (100 MB) dosyaları dener.",
            ],
            key="benchmark_modu",
            label_visibility="collapsed",
            disabled=st.session_state.test_calisiyor,
        )
        karma_mod = secilen_mod == "Karma İş Yükü"
        sweep_mod = secilen_mod == "Concurrency Sweep"
        matrix_mod = secilen_mod == "Değişken Boyut Matrisi"

        karma_ayarlar = {}
        if karma_mod:
            st.caption("Karma Ayarları")
            sure_sn      = st.slider("Süre (sn)",   10, 300, 60, 10, key="karma_sure")
            upload_pct   = st.slider("Upload %",    0, 100,  20,  5, key="karma_upload_pct")
            download_pct = st.slider("Download %",  0, 100 - upload_pct, 70, 5, key="karma_download_pct")
            head_pct     = 100 - upload_pct - download_pct
            st.caption(f"HeadObject: **%{head_pct}** (otomatik)")
            karma_ayarlar = {
                "sure_sn":           sure_sn,
                "upload_agirlik":    upload_pct,
                "download_agirlik":  download_pct,
                "head_agirlik":      head_pct,
            }

        matrix_ayarlari = None
        if matrix_mod:
            st.caption("Matris Ayarları (Örn: 4 KB ve 1000 MB)")
            st.markdown("**Grup 1 (Küçük Dosyalar)**")
            g1_count = st.number_input("Grup 1 Dosya Sayısı", min_value=1, value=10, key="g1_count")
            g1_size = st.number_input("Grup 1 Boyut (MB)", min_value=0.001, value=0.004, step=0.001, format="%.3f", key="g1_size")
            
            st.markdown("**Grup 2 (Büyük Dosyalar)**")
            g2_count = st.number_input("Grup 2 Dosya Sayısı", min_value=1, value=2, key="g2_count")
            g2_size = st.number_input("Grup 2 Boyut (MB)", min_value=1.0, value=100.0, step=1.0, key="g2_size")
            
            matrix_ayarlari = [
                {"count": g1_count, "min_mb": g1_size, "max_mb": g1_size},
                {"count": g2_count, "min_mb": g2_size, "max_mb": g2_size},
            ]

        # ── Bucket Klasörleri ─────────────────────────────────────────────────
        st.divider()
        st.markdown("### Bucket Klasörleri")
        if bucket_name and endpoint and access_key and secret_key:
            try:
                prefixes = s3_utils.list_prefixes(bucket_name, endpoint, access_key, secret_key)
                if not prefixes:
                    st.caption("Klasör bulunamadı.")
                else:
                    for idx, p in enumerate(prefixes):
                        c_isim, c_btn = st.columns([3, 1], vertical_alignment="center")
                        c_isim.caption(f"{p}")
                        if c_btn.button("Sil", key=f"del_{p}_{idx}", help=f"{p} klasörünü sil"):
                            if s3_utils.delete_prefix(bucket_name, p, endpoint, access_key, secret_key):
                                st.success(f"{p} silindi")
                                st.rerun()
                            else:
                                st.error("Silinemedi")
            except Exception as e:
                st.error(f"S3 hatası: {e}")
        else:
            st.caption("Bağlantı bilgilerini doldurun.")

    return dict(
        endpoint=endpoint, access_key=access_key, secret_key=secret_key,
        bucket_name=bucket_name, test_adi=test_adi,
        secilen_profil=secilen_profil, ozel_ayarlar_kullan=ozel_ayarlar,
        auto_temizle=auto_temizle, isinma_evresi=isinma_evresi,
        karma_mod=karma_mod, karma_ayarlar=karma_ayarlar,
        sweep_mod=sweep_mod, matrix_mod=matrix_mod, matrix_ayarlari=matrix_ayarlari,
        ayarlar=dict(
            file_count=int(file_count),
            file_size_min_mb=float(file_size_min_mb),
            file_size_max_mb=float(file_size_max_mb),
            concurrency=int(concurrency),
        ),
    )


def delete_paneli(prefix: str, endpoint: str, access_key: str,
                  secret_key: str, bucket_name: str) -> None:
    """Test sonrası 'Sil ve Ölç' (Delete Benchmark) bileşenini gösterir."""
    if not prefix:
        return

    if st.session_state.delete_calisiyor:
        st.info("Delete benchmark devam ediyor…")
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
            st.session_state.delete_hata  = None
            st.session_state.delete_output = {}
            dt = threading.Thread(
                target=delete_thread_fn,
                args=(endpoint, access_key, secret_key, bucket_name,
                      prefix, st.session_state.delete_output),
                daemon=True,
            )
            st.session_state.delete_thread = dt
            dt.start()
            st.rerun()

    if st.session_state.delete_hata:
        st.error(f"Delete hatası: {st.session_state.delete_hata}")
    elif st.session_state.delete_sonuc:
        ds = st.session_state.delete_sonuc
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Toplam Nesne", ds.get("toplam_nesne", 0))
        d2.metric("Silinen",      ds.get("basarili_silinen", 0))
        d3.metric("Süre",         f"{ds.get('toplam_sure_sn', 0):.3f} sn")
        d4.metric("Hız",          f"{ds.get('ops_per_sec', 0):.1f} ops/sn")
