"""
tests/test_history.py — history.py modülü testleri.
"""

import os
import pandas as pd
from analytics import history


def test_gecmis_kaydet_ve_oku(tmp_path, monkeypatch):
    """Geçmişe kayıt ekleme ve okuma işlevini test eder."""
    gecmis_dosya = str(tmp_path / "test_gecmisi.csv")
    monkeypatch.setattr(history, "GECMIS_DOSYA", gecmis_dosya)

    ozet = {
        "ortalama_sure": 0.5,
        "en_hizli": 0.1,
        "en_yavas": 1.0,
        "p95": 0.8,
        "p99": 0.9,
        "toplam_throughput_mb_s": 15.0,
        "upload_throughput_mb_s": 8.0,
        "download_throughput_mb_s": 7.0,
        "multipart_upload_throughput_mb_s": 0.0,
        "list_objects_ops_per_sec": 10.0,
        "head_object_ops_per_sec": 50.0,
        "delete_ops_per_sec": 0.0,
    }

    # Kaydet
    history.kaydet(profil_adi="hizli", bucket_name="test-bucket", ozet=ozet, test_adi="NVMe-Test-1")

    assert os.path.exists(gecmis_dosya)

    # Oku
    df = history.gecmisi_oku()
    assert df is not None
    assert len(df) == 1
    assert df.iloc[0]["test_adi"] == "NVMe-Test-1"
    assert df.iloc[0]["bucket"] == "test-bucket"


def test_isim_guncelle(tmp_path, monkeypatch):
    """Test adının yeniden adlandırılabildiğini doğrular."""
    gecmis_dosya = str(tmp_path / "test_gecmisi.csv")
    monkeypatch.setattr(history, "GECMIS_DOSYA", gecmis_dosya)

    ozet = {"ortalama_sure": 0.5, "p95": 0.8, "toplam_throughput_mb_s": 10.0}
    history.kaydet(profil_adi="hizli", bucket_name="test-bucket", ozet=ozet, test_adi="Eski-Isim")

    df = history.gecmisi_oku()
    test_id = df.iloc[0]["test_id"]

    # İsim güncelle
    basarili = history.isim_guncelle(test_id, "Yeni-Isim")
    assert basarili is True

    guncel_df = history.gecmisi_oku()
    assert guncel_df.iloc[0]["test_adi"] == "Yeni-Isim"
