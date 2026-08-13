"""
ui/tabs/live_tab.py — 📡 Canlı İzleme Sekmesi.

Test çalışırken:
  - Anlık durum mesajı
  - 5'li KPI barı (anlık sayaçlar)
  - 2x2 kompakt grafik grid (Throughput / Latency / CPU&RAM / Ağ)
  - Thread bitişini izleyerek session_state'i günceller
Test çalışmıyorken:
  - Boş grafik placeholder grid'i gösterir
"""

import time

import streamlit as st

from analytics import metrics
from ui.components import kpi_bari
from ui.charts import grafik_paneli


def render(ctx: dict) -> None:
    """
    Canlı İzleme Sekmesi içeriğini çizer.

    Parameters
    ----------
    ctx : dict — render() tarafından iletilen bağlam sözlüğü:
        - "thread_output" paylaşımlı çıktı dict'i (session_state'e yazılır)
    """
    if st.session_state.test_calisiyor:
        thread = st.session_state.benchmark_thread
        st.info(f"⚙️ {metrics.get_status()}")

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

        if thread and thread.is_alive():
            time.sleep(1.5)
            st.rerun()
        else:
            # Thread tamamlandı — sonuçları session_state'e yaz
            st.session_state.test_calisiyor = False
            output = st.session_state.thread_output
            if "hata" in output:
                st.session_state.benchmark_hata = output["hata"]
            elif "sonuc" in output:
                st.session_state.benchmark_sonuc = output["sonuc"]
            elif "karma_sonuc" in output:
                st.session_state.karma_sonuc = output["karma_sonuc"]
            st.rerun()
    else:
        # Test çalışmıyorken boş placeholder grid
        grafik_paneli()
