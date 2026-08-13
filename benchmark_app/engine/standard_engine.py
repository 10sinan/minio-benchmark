"""
engine/standard_engine.py — Standart Benchmark Motoru.

Standart akış:
  1. Dosya üretimi (generator)
  2. Upload + Multipart Upload (uploader)
  3. Download (downloader)
  4. Metadata benchmark — ListObjectsV2 + HeadObject (metadata_ops)
  5. Kaynak izleyici (resource_monitor) tüm akış boyunca çalışır
"""
import logging
import pandas as pd

from core import generator, uploader, downloader, metadata_ops
from analytics import metrics, reporter, resource_monitor


def run_benchmark(
    ayarlar,
    endpoint,
    access_key,
    secret_key,
    bucket_name,
    test_prefix,
    matrix_ayarlari=None,
    folder_path="generated_files",
    indirilecek_klasor="downloaded_files",
    iptal_kontrol=None,
):
    """
    Tam standart benchmark akışını çalıştırır.

    Returns
    -------
    tuple : (df, ozet, upload_df, download_df)
    """
    metrics.kuyrugu_temizle()
    resource_monitor.temizle()
    resource_monitor.baslat(aralik_sn=0.5)

    logging.info(
        "Benchmark başlatılıyor: prefix=%s, file_count=%s",
        test_prefix,
        ayarlar.get("file_count"),
    )

    try:
        # ── Adım 1: Dosya Üretimi ────────────────────────────────────────────────
        metrics.set_status("Dosyalar üretiliyor…")
        generator.generate_files(
            folder_path=folder_path,
            file_count=ayarlar.get("file_count"),
            file_size_min_mb=ayarlar.get("file_size_min_mb"),
            file_size_max_mb=ayarlar.get("file_size_max_mb"),
            matrix_ayarlari=matrix_ayarlari,
        )

        if iptal_kontrol and iptal_kontrol():
            logging.info("Benchmark iptal edildi (dosya üretiminden sonra).")
            return _bos_sonuc()

        # ── Adım 2: Upload (+ Multipart kıyaslaması) ─────────────────────────────
        uploader.upload_files(
            folder_path=folder_path,
            bucket_name=bucket_name,
            endpoint_url=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            concurrency=ayarlar.get("concurrency", 4),
            prefix=test_prefix,
            iptal_kontrol=iptal_kontrol,
        )

        if iptal_kontrol and iptal_kontrol():
            logging.info("Benchmark iptal edildi (upload sonrası).")
            return _sonuc_topla()

        # ── Adım 3: Download ─────────────────────────────────────────────────────
        downloader.download_files(
            bucket_name=bucket_name,
            endpoint_url=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            indirilecek_klasor=indirilecek_klasor,
            concurrency=ayarlar.get("concurrency", 4),
            prefix=test_prefix,
            iptal_kontrol=iptal_kontrol,
        )

        if iptal_kontrol and iptal_kontrol():
            logging.info("Benchmark iptal edildi (download sonrası).")
            return _sonuc_topla()

        # ── Adım 4: Metadata benchmark — List + Head ─────────────────────────────
        metadata_ops.benchmark_list_objects(
            bucket_name=bucket_name,
            endpoint_url=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            prefix=test_prefix,
            tekrar=10,
        )

        if not (iptal_kontrol and iptal_kontrol()):
            metadata_ops.benchmark_head_object(
                bucket_name=bucket_name,
                endpoint_url=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                prefix=test_prefix,
                concurrency=ayarlar.get("concurrency", 4),
            )
    finally:
        resource_monitor.durdur()

    metrics.set_status("Tamamlandı")
    logging.info("Benchmark tamamlandı: prefix=%s", test_prefix)
    return _sonuc_topla()


def _sonuc_topla():
    """Toplanan metrikleri reporter'dan geçirir ve standart tuple döndürür."""
    sonuclar = metrics.tum_sonuclari_al()
    df = reporter.tabloya_cevir(sonuclar)
    ozet = reporter.ozet_cikar(df)

    if df.empty:
        return df, ozet, df.copy(), df.copy()

    upload_df = _filtrele_ve_mb(df, "upload")
    download_df = _filtrele_ve_mb(df, "download")
    return df, ozet, upload_df, download_df


def _filtrele_ve_mb(df, islem_tipi):
    """Verilen işlem tipini filtreler ve boyut_byte sütununu MB'a çevirir."""
    alt = df[df["islem_tipi"] == islem_tipi].copy()
    if "boyut_byte" in alt.columns:
        alt["boyut_mb"] = alt["boyut_byte"] / (1024 * 1024)
        alt = alt.drop(columns=["boyut_byte"])
    return alt


def _bos_sonuc():
    df = pd.DataFrame()
    return df, reporter.ozet_cikar(df), df.copy(), df.copy()
