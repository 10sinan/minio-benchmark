"""
analytics/resource_monitor.py — İstemci taraflı kaynak izleyici.

Test esnasında benchmark makinesinin CPU, RAM ve Ağ trafiğini
psutil ile arka planda ölçer.

Herhangi bir S3 sağlayıcısıyla uyumludur (AWS S3, MinIO, Wasabi,
Cloudflare R2, Backblaze B2 vb.) — sunucu tarafına hiç dokunmaz.
"""
import threading
import time
import logging

try:
    import psutil
    PSUTIL_MEVCUT = True
except ImportError:
    PSUTIL_MEVCUT = False
    logging.warning("psutil kurulu değil — kaynak izleme devre dışı.")

# ── Modül düzeyinde durum ────────────────────────────────────────────────────
_lock = threading.Lock()
_veri: list = []
_stop_event = threading.Event()
_thread: threading.Thread | None = None


# ── Dışarıya açık API ────────────────────────────────────────────────────────

def baslat(aralik_sn: float = 0.5) -> None:
    """Kaynak izlemeyi arka plan thread'inde başlatır."""
    global _thread
    if not PSUTIL_MEVCUT:
        logging.warning("psutil eksik, kaynak izleme başlatılamadı.")
        return
    _stop_event.clear()
    with _lock:
        _veri.clear()
    _thread = threading.Thread(target=_topla, args=(aralik_sn,), daemon=True)
    _thread.start()
    logging.info("Kaynak izleyici başlatıldı (aralık=%.1fs).", aralik_sn)


def durdur() -> None:
    """Kaynak izlemeyi durdurur ve thread'in bitmesini bekler."""
    _stop_event.set()
    if _thread and _thread.is_alive():
        _thread.join(timeout=3)
    logging.info("Kaynak izleyici durduruldu.")


def get_data() -> list:
    """
    Toplanan kaynak metriklerinin anlık kopyasını döndürür.
    UI polling döngüsünden thread-safe olarak çağrılabilir.
    """
    with _lock:
        return list(_veri)


def temizle() -> None:
    """Toplanan verileri sıfırlar."""
    with _lock:
        _veri.clear()


# ── İç toplama döngüsü ───────────────────────────────────────────────────────

def _topla(aralik_sn: float) -> None:
    """
    Her `aralik_sn` saniyede bir CPU, RAM ve Ağ anlık görüntüsü alır.
    Ağ hızı önceki ölçümle delta alınarak MB/sn cinsinden hesaplanır.
    """
    prev_net = psutil.net_io_counters()
    prev_zaman = time.time()

    while not _stop_event.is_set():
        time.sleep(aralik_sn)
        if _stop_event.is_set():
            break

        simdi = time.time()
        dt = simdi - prev_zaman

        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory()
            net = psutil.net_io_counters()
        except Exception as e:
            logging.warning("psutil okuma hatası: %s", e)
            continue

        if dt > 0:
            gonderilen_mb_s = (net.bytes_sent - prev_net.bytes_sent) / (1024 * 1024) / dt
            alinan_mb_s = (net.bytes_recv - prev_net.bytes_recv) / (1024 * 1024) / dt
        else:
            gonderilen_mb_s = alinan_mb_s = 0.0

        with _lock:
            _veri.append(
                {
                    "zaman": simdi,
                    "cpu_pct": cpu,
                    "ram_mb": ram.used / (1024 * 1024),
                    "ram_pct": ram.percent,
                    "net_gonderilen_mb_s": max(0.0, gonderilen_mb_s),
                    "net_alinan_mb_s": max(0.0, alinan_mb_s),
                }
            )

        prev_net = net
        prev_zaman = simdi
