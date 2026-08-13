"""
tests/conftest.py — Pytest paylaşılan fixture'ları.
"""

import pandas as pd
import pytest


@pytest.fixture
def ornek_metrik_df():
    """Raporlama ve istatistik testleri için örnek benchmark verisi üretir."""
    data = [
        {"islem_tipi": "upload", "sure": 0.5, "boyut_byte": 1048576, "basarili": True},
        {"islem_tipi": "upload", "sure": 1.0, "boyut_byte": 1048576, "basarili": True},
        {"islem_tipi": "download", "sure": 0.2, "boyut_byte": 1048576, "basarili": True},
        {"islem_tipi": "download", "sure": 0.4, "boyut_byte": 1048576, "basarili": True},
        {"islem_tipi": "head_object", "sure": 0.05, "boyut_byte": None, "basarili": True},
    ]
    return pd.DataFrame(data)


@pytest.fixture
def ornek_ayarlar():
    """Test profili ve eşik değerleri (thresholds) sözlüğü."""
    return {
        "file_count": 10,
        "file_size_min_mb": 1.0,
        "file_size_max_mb": 1.0,
        "concurrency": 4,
        "thresholds": {
            "latency_iyi_sn": 1.0,
            "latency_orta_sn": 3.0,
            "throughput_iyi_mb_s": 5.0,
            "throughput_orta_mb_s": 2.0,
        },
    }
