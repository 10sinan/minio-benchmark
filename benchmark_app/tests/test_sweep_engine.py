"""
tests/test_sweep_engine.py — Sweep Motoru birim testi.
"""

from unittest.mock import patch
import pandas as pd
from engine import sweep_engine


@patch("engine.sweep_engine.standard_engine.run_benchmark")
def test_run_concurrency_sweep(mock_run_benchmark):
    """
    Sweep motorunun [1, 2, 4, 8, 16, 32] concurrency seviyelerinde
    doğru şekilde çalışıp her seviyeyi tabloya eklediğini doğrular.
    """
    # Her çağrıldığında dönecek sahte değer (df, ozet, upload_df, download_df)
    mock_run_benchmark.return_value = (
        pd.DataFrame(),
        {"toplam_dosya": 10, "toplam_throughput_mb_s": 50.0},
        pd.DataFrame(),
        pd.DataFrame(),
    )

    ayarlar = {"file_count": 10}
    
    sweep_df = sweep_engine.run_concurrency_sweep(
        ayarlar=ayarlar,
        endpoint="http://dummy",
        access_key="dummy",
        secret_key="dummy",
        bucket_name="test-bucket",
        test_prefix_base="sweep_test",
    )

    # 1, 2, 4, 8, 16, 32 olmak üzere toplam 6 kez çağrılmalı
    assert mock_run_benchmark.call_count == 6
    assert len(sweep_df) == 6

    # Geri dönen dataframe içinde concurrency sütunu bulunmalı ve doğru değerleri almalı
    beklenen_seviyeler = [1, 2, 4, 8, 16, 32]
    assert sweep_df["concurrency"].tolist() == beklenen_seviyeler

    # Ozet bilgilerinin de kopyalandığını doğrulayalım
    assert (sweep_df["toplam_dosya"] == 10).all()
