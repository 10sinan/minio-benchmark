"""
tests/test_ui_state.py — ui/state.py modülü testleri.
"""

from ui.state import olustur_test_prefix


def test_olustur_test_prefix_ozel_karakterler():
    """Özel karakterlerin ve boşlukların alt çizgiye dönüştüğünü doğrular."""
    prefix = olustur_test_prefix("NVMe Cluster #1 (Test)")

    assert "NVMe_Cluster__1__Test_" in prefix
    assert not any(c in prefix for c in [" ", "#", "(", ")"])


def test_olustur_test_prefix_bos_girdi():
    """Boş girdi verildiğinde varsayılan 'test_' prefix'i üretildiğini doğrular."""
    prefix = olustur_test_prefix("   ")

    assert prefix.startswith("test_")
