"""
metrics.py — Thread-safe metrik toplayıcı.

Tek bir global liste ve Lock kullanır. Benchmark thread'i veri yazarken
Streamlit UI thread'i listeyi tüketmeden okuyabilir (canlı grafik için).
"""
import threading
import time

_lock = threading.Lock()
_metrikler: list = []
_status: str = "Hazır"


# ---------------------------------------------------------------------------
# Durum Yönetimi
# ---------------------------------------------------------------------------

def set_status(durum: str) -> None:
    global _status
    _status = durum


def get_status() -> str:
    return _status


# ---------------------------------------------------------------------------
# Metrik Yazma / Okuma
# ---------------------------------------------------------------------------

def kuyrugu_temizle() -> None:
    """Yeni bir test başlamadan önce önceki metrikleri temizler."""
    with _lock:
        _metrikler.clear()


def kaydet(
    dosya_adi: str,
    sure: float,
    basarili: bool,
    islem_tipi: str,
    boyut_byte: int | None = None,
    zaman: float | None = None,
) -> None:
    """
    Tek bir işlem sonucunu thread-safe şekilde kaydeder.

    Parameters
    ----------
    dosya_adi   : Dosya adı veya nesne anahtarı
    sure        : İşlem süresi (saniye)
    basarili    : Başarı durumu
    islem_tipi  : 'upload', 'download', 'multipart_upload',
                  'list_objects', 'head_object', 'delete'
    boyut_byte  : Nesne boyutu (byte), varsa
    zaman       : Unix timestamp (varsayılan: şimdiki an)
    """
    if zaman is None:
        zaman = time.time()
    with _lock:
        _metrikler.append(
            {
                "dosya_adi": dosya_adi,
                "sure": sure,
                "basarili": basarili,
                "islem_tipi": islem_tipi,
                "boyut_byte": boyut_byte,
                "zaman": zaman,
            }
        )


def anlık_kopyala() -> list:
    """
    UI thread'inin canlı grafik çizmesi için mevcut metrik listesinin
    kopyasını döndürür. Listeyi tüketmez (kuyruğun aksine).
    """
    with _lock:
        return list(_metrikler)


def tum_sonuclari_al() -> list:
    """
    Benchmark tamamlandıktan sonra tüm metriklerin kopyasını döndürür.
    Geriye uyumluluk için `anlık_kopyala` ile aynı davranışı gösterir.
    """
    return anlık_kopyala()