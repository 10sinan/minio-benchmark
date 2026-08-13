import os
# proxy engelleme için
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)

from ui.log_stream import handler_kur
handler_kur()  # Canlı log toplayıcıyı başlat

from ui import render

if __name__ == "__main__":
    render()