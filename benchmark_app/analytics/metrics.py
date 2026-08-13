"""
metrics.py

Thread-safe metrik toplayıcı. Benchmark thread'i veri yazarken
Streamlit UI thread'i aynı anda okuyabilir; kilitlenme olmaz.
"""
import threading
import time

_lock = threading.Lock()
_metrikler: list = []
_status: str = "Hazır"


# ---------------------------------------------------------------------------
# Durum Mesajı
# ---------------------------------------------------------------------------

def set_status(durum: str) -> None:
    global _status
    _status = durum


def get_status() -> str:
    return _status


# ---------------------------------------------------------------------------
# Metrik Kayıt ve Okuma
# ---------------------------------------------------------------------------

def kuyrugu_temizle() -> None:
    """Yeni bir test veya ısınma evresi başlamadan önce önceki verileri siler."""
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
    Bir işlem sonucunu güvenli şekilde listeye ekler.

    Parameters
    ----------
    dosya_adi   : Dosya adı veya S3 nesne anahtarı
    sure        : İşlem süresi (saniye)
    basarili    : Başarı durumu
    islem_tipi  : 'upload', 'download', 'multipart_upload',
                  'list_objects', 'head_object', 'delete'
    boyut_byte  : Nesne boyutu (byte), varsa
    zaman       : Unix timestamp; verilmezse şimdiki an kullanılır
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
    Canlı grafik için mevcut metrik listesinin anlık kopyasını döndürür.
    Listeyi temizlemez; sadece okur.
    """
    with _lock:
        return list(_metrikler)


def tum_sonuclari_al() -> list:
    """
    Test bittikten sonra tüm metrikleri döndürür.
    Geriye uyumluluk için anlık_kopyala ile aynı davranışı gösterir.
    """
    return anlık_kopyala()