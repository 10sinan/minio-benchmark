"""
ui/tabs/live_tab.py — Canlı İzleme Sekmesi.

Test çalışırken:
  - Anlık durum mesajı
  - 5'li KPI barı (anlık sayaçlar)
  - 2x2 kompakt grafik grid (Throughput / Latency / CPU&RAM / Ağ)
  - Thread bitişini izleyerek session_state'i günceller
  - Canlı Log Paneli
"""

import time

import streamlit as st

from analytics import metrics
from ui.components import kpi_bari
from ui.charts import grafik_paneli
from ui import log_stream
from ui.theme import RENKLER


def render(ctx: dict) -> None:
    """Canlı İzleme Sekmesi içeriğini çizer."""
    if st.session_state.test_calisiyor:
        thread = st.session_state.benchmark_thread
        st.info(f"{metrics.get_status()}")

        # Anlık KPI barı
        anlık_liste = metrics.anlık_kopyala()
        anlık_ozet = {
            "toplam_dosya": len(anlık_liste),
            "basarili":     sum(1 for m in anlık_liste if m.get("basarili")),
            "hatali":       sum(1 for m in anlık_liste if not m.get("basarili")),
            "toplam_throughput_mb_s": 0.0,
            "p95": 0.0,
        }
        kpi_bari(anlık_ozet)

        # 2x2 Grafik grid
        grafik_paneli()

        # Canlı Log Paneli
        _log_paneli(canli=True)

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
            elif "sweep_sonuc" in output:
                st.session_state.sweep_sonuc = output["sweep_sonuc"]
            st.rerun()
    else:
        grafik_paneli()
        _log_paneli(canli=False)


def _log_paneli(canli: bool = False) -> None:
    """Canlı veya geçmiş log kayıtlarını genişletilebilir bir expander içinde gösterir."""
    baslik = "Canlı Loglar" if canli else "Son Loglar"
    kayitlar = log_stream.son_kayitlar(n=60)

    with st.expander(baslik, expanded=canli):
        if not kayitlar:
            st.caption("Henüz log kaydı yok.")
            return

        for kayit in reversed(kayitlar):
            seviye = kayit["seviye"]
            renk   = log_stream.LOG_SEVIYE_RENK.get(seviye, RENKLER["metin_ikincil"])
            mesaj  = kayit["mesaj"]
            st.markdown(
                f'<span style="color:{renk};font-family:monospace;font-size:12px;">'
                f'{mesaj}</span>',
                unsafe_allow_html=True,
            )

        if canli:
            col1, _ = st.columns([1, 5])
            if col1.button("Logları Temizle", key="log_temizle_btn"):
                log_stream.temizle()
                st.rerun()
