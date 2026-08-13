"""
tests/test_reporter.py — reporter.py modülü birim testleri.
"""

from analytics import reporter


def test_ozet_cikar_hesaplama(ornek_metrik_df):
    """ozet_cikar fonksiyonunun Throughput ve süre metriklerini doğru hesapladığını doğrular."""
    ozet = reporter.ozet_cikar(ornek_metrik_df)

    assert ozet["toplam_dosya"] == 5
    assert ozet["basarili"] == 5
    assert ozet["hatali"] == 0
    assert ozet["en_hizli"] == 0.05
    assert ozet["en_yavas"] == 1.0
    assert ozet["upload_throughput_mb_s"] > 0
    assert ozet["download_throughput_mb_s"] > 0


def test_durum_degerlendir_basarili(ornek_ayarlar):
    """Yüksek performanslı özetin durum durumlarını doğrular."""
    ozet = {
        "toplam_dosya": 10,
        "basarili": 10,
        "hatali": 0,
        "toplam_throughput_mb_s": 10.0,
        "p95": 0.5,
    }
    thresholds = ornek_ayarlar["thresholds"]
    durum = reporter.durum_degerlendir(ozet, thresholds)

    assert durum["latency_durum"] == "İyi"
    assert durum["basari_durum"] == "Mükemmel"
    assert durum["throughput_durum"] == "İyi"


def test_durum_degerlendir_yavas_throughput(ornek_ayarlar):
    """Throughput eşiğin altında kaldığında durumun 'Yavaş' olduğunu doğrular."""
    ozet = {
        "toplam_dosya": 10,
        "basarili": 10,
        "hatali": 0,
        "toplam_throughput_mb_s": 1.0,  # Min 5.0 olmalıydı (orta: 2.0)
        "p95": 0.5,
    }
    thresholds = ornek_ayarlar["thresholds"]
    durum = reporter.durum_degerlendir(ozet, thresholds)

    assert durum["throughput_durum"] == "Yavaş"
