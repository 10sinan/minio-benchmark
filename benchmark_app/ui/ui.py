"""
ui/ui.py — Ana Render Orkestratörü.

Bu dosya yalnızca bileşenleri bir araya getiren ince bir orkestratördür.
Tüm iş mantığı ayrı modüllerde yaşar:

  Bileşen          → Modül
  ──────────────────────────────────────────
  Session State    → ui/state.py
  Sidebar          → ui/components.py
  KPI Barı         → ui/components.py
  Sil ve Ölç       → ui/components.py
  2x2 Grafik Grid  → ui/charts.py
  Canlı İzleme     → ui/tabs/live_tab.py
  Detaylar         → ui/tabs/details_tab.py
  Geçmiş           → ui/tabs/history_tab.py
  CSS & Plotly     → ui/theme.py
"""

import logging
import threading

import streamlit as st
import yaml

from core import s3_utils
from ui.state import init_state, benchmark_thread_fn, karma_thread_fn, olustur_test_prefix
from ui.theme import inject_apple_hig_css
from ui.components import sidebar
from ui.tabs import live_tab, details_tab, history_tab

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# ──────────────────────────────────────────────────────────────────────────────
# Ana Render Fonksiyonu
# ──────────────────────────────────────────────────────────────────────────────

def render() -> None:
    """Streamlit uygulamasını başlatır ve tüm bileşenleri orkestre eder."""
    init_state()
    st.set_page_config(
        page_title="S3 Benchmark",
        layout="wide",
        page_icon="📐",
        initial_sidebar_state="expanded",
    )
    inject_apple_hig_css()

    # Config dosyasını yükle
    try:
        with open("config.yaml", "r") as f:
            settings = yaml.safe_load(f)
    except Exception as e:
        st.error(f"config.yaml okunamadı: {e}")
        return

    # ── Sol Sidebar ───────────────────────────────────────────────────────────
    cfg = sidebar(settings)
    endpoint            = cfg["endpoint"]
    access_key          = cfg["access_key"]
    secret_key          = cfg["secret_key"]
    bucket_name         = cfg["bucket_name"]
    test_adi            = cfg["test_adi"]
    secilen_profil      = cfg["secilen_profil"]
    ozel_ayarlar_kullan = cfg["ozel_ayarlar_kullan"]
    auto_temizle        = cfg["auto_temizle"]
    karma_mod           = cfg["karma_mod"]
    karma_ayarlar       = cfg["karma_ayarlar"]
    ayarlar             = cfg["ayarlar"]

    # ── Başlık ────────────────────────────────────────────────────────────────
    st.markdown("## 📐 S3 Benchmark")

    # ── Kontrol Barı ─────────────────────────────────────────────────────────
    cb1, cb2, _cb3, _cb4 = st.columns([1, 1, 1, 6])
    start_btn = cb1.button("▶ Başlat", type="primary",
                           disabled=st.session_state.test_calisiyor, key="start_btn")
    stop_btn  = cb2.button("⏹ Durdur",
                           disabled=not st.session_state.test_calisiyor, key="stop_btn")

    if stop_btn:
        st.session_state.iptal_event.set()
        st.warning("İptal isteği gönderildi…")

    # ── Test Başlatma ─────────────────────────────────────────────────────────
    if start_btn:
        if not all([endpoint, access_key, secret_key, bucket_name]):
            st.error("Lütfen tüm bağlantı bilgilerini sidebar'dan doldurun.")
        else:
            try:
                with st.spinner("Bağlantı kontrol ediliyor…"):
                    s3_utils.baglanti_kontrolu(endpoint, access_key, secret_key, bucket_name)
            except Exception as hata:
                st.error(f"Bağlantı hatası: {hata}")
            else:
                test_prefix = olustur_test_prefix(test_adi)

                # Session state sıfırla
                st.session_state.update({
                    "test_calisiyor":   True,
                    "benchmark_sonuc":  None,
                    "karma_sonuc":      None,
                    "benchmark_hata":   None,
                    "thread_output":    {},
                    "son_prefix":       test_prefix,
                    "delete_sonuc":     None,
                    "delete_hata":      None,
                })
                st.session_state.iptal_event.clear()

                iptal_fn = st.session_state.iptal_event.is_set

                if karma_mod:
                    thread = threading.Thread(
                        target=karma_thread_fn,
                        args=(ayarlar, endpoint, access_key, secret_key, bucket_name,
                              test_prefix, karma_ayarlar, iptal_fn,
                              st.session_state.thread_output),
                        daemon=True,
                    )
                else:
                    thread = threading.Thread(
                        target=benchmark_thread_fn,
                        args=(ayarlar, endpoint, access_key, secret_key, bucket_name,
                              test_prefix, iptal_fn, st.session_state.thread_output),
                        daemon=True,
                    )

                st.session_state.benchmark_thread = thread
                thread.start()
                st.rerun()

    # ── Sekmeler ──────────────────────────────────────────────────────────────
    tab_canli, tab_detay, tab_gecmis = st.tabs(
        ["📡 Canlı İzleme", "🔍 Detaylar", "📜 Geçmiş & Karşılaştır"]
    )

    with tab_canli:
        live_tab.render(ctx={})

    with tab_detay:
        details_tab.render(ctx=dict(
            endpoint=endpoint, access_key=access_key,
            secret_key=secret_key, bucket_name=bucket_name,
            test_adi=test_adi, secilen_profil=secilen_profil,
            ozel_ayarlar_kullan=ozel_ayarlar_kullan,
            auto_temizle=auto_temizle,
            settings=settings,
        ))

    with tab_gecmis:
        history_tab.render()


if __name__ == "__main__":
    render()