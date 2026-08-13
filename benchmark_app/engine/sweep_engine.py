"""
engine/sweep_engine.py — Concurrency Sweep Motoru.

Farklı thread (concurrency) seviyelerinde standart benchmark akışını
otomatik olarak tekrar tekrar çalıştırarak sistemin darboğaz noktasını (bottleneck) bulur.
"""
import logging
import pandas as pd

from engine import standard_engine


def run_concurrency_sweep(
    ayarlar,
    endpoint,
    access_key,
    secret_key,
    bucket_name,
    test_prefix_base,
    folder_path="generated_files",
    indirilecek_klasor="downloaded_files",
    iptal_kontrol=None,
):
    """
    Belirtilen thread seviyelerinde (1, 2, 4, 8, 16, 32) sırasıyla
    standart benchmark testini çalıştırır.

    Returns
    -------
    pd.DataFrame : Her bir concurrency seviyesinin performans özetlerini içeren tablo.
    """
    sweep_levels = [1, 2, 4, 8, 16, 32]
    ozetler = []

    for level in sweep_levels:
        if iptal_kontrol and iptal_kontrol():
            logging.info("Concurrency Sweep iptal edildi.")
            break

        logging.info(f"Sweep çalıştırılıyor: Concurrency = {level}")
        
        # Ayarları o anki thread sayısına göre güncelle
        ayarlar_kopya = ayarlar.copy()
        ayarlar_kopya["concurrency"] = level

        # Klasörlerin birbiriyle çakışmaması için prefix'e thread sayısını ekle
        prefix = f"{test_prefix_base}_c{level}"

        # Standart benchmark'ı çalıştır
        _, ozet, _, _ = standard_engine.run_benchmark(
            ayarlar=ayarlar_kopya,
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            bucket_name=bucket_name,
            test_prefix=prefix,
            folder_path=folder_path,
            indirilecek_klasor=indirilecek_klasor,
            iptal_kontrol=iptal_kontrol,
        )

        # Hangi thread seviyesinde koştuğunu özete ekleyelim
        ozet_kopya = ozet.copy()
        ozet_kopya["concurrency"] = level
        ozetler.append(ozet_kopya)

    sweep_df = pd.DataFrame(ozetler)
    return sweep_df
