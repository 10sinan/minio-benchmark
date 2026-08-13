"""
ui/log_stream.py — Canlı Log Toplayıcı.

Uygulama genelindeki Python loglarını bellek içinde tutar.
Streamlit arayüzünden bu logu okuyup göstermek için kullanılır.
"""

import logging
from collections import deque

# Son 200 log kaydını bellekte tut
_LOG_KAYITLARI: deque = deque(maxlen=200)

LOG_SEVIYE_RENK = {
    "DEBUG":    "#64D2FF",   # Teal
    "INFO":     "#30D158",   # Yeşil
    "WARNING":  "#FFD60A",   # Sarı
    "ERROR":    "#FF453A",   # Kırmızı
    "CRITICAL": "#FF453A",   # Kırmızı
}


class StreamlitLogHandler(logging.Handler):
    """Uygulama loglarını deque'ye yazan özel logging handler."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            _LOG_KAYITLARI.append({
                "seviye": record.levelname,
                "mesaj": self.format(record),
                "zaman": record.created,
            })
        except Exception:
            pass


def handler_kur() -> None:
    """
    Kök logger'a StreamlitLogHandler'ı ekler.
    Yalnızca bir kez çağrılmalıdır (app.py veya ui.py başında).
    """
    kok_logger = logging.getLogger()
    # Aynı handler'ı iki kez eklememek için kontrol
    for h in kok_logger.handlers:
        if isinstance(h, StreamlitLogHandler):
            return
    handler = StreamlitLogHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s",
                                           datefmt="%H:%M:%S"))
    handler.setLevel(logging.DEBUG)
    kok_logger.addHandler(handler)


def son_kayitlar(n: int = 50) -> list:
    """Son n log kaydını liste olarak döndürür (en yeni en sonda)."""
    kayitlar = list(_LOG_KAYITLARI)
    return kayitlar[-n:]


def temizle() -> None:
    """Log kaydını temizler."""
    _LOG_KAYITLARI.clear()
