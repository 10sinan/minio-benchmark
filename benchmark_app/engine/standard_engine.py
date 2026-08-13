"""
engine/standard_engine.py

Upload, download ve metadata işlemlerini sırayla koşturan standart test akışı.
İsteğe bağlı ısınma evresi ile sistemi sıcak başlatır.
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
    Standart benchmark akışını baştan sona çalıştırır.

    Returns
    -------
    tuple : (df, ozet, upload_df, download_df, res_data)
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
        # İstenirse önce ısınma evresi çalışır, bittikten sonra sayaç sıfırlanır
        isinma = ayarlar.get("isinma_evresi", False)
        if isinma:
            _isinma_evresi_calistir(
                endpoint, access_key, secret_key, bucket_name, test_prefix + "_warmup"
            )
            if iptal_kontrol and iptal_kontrol():
                return _bos_sonuc()

        # ── 1. Dosya Üretimi ──────────────────────────────────────────────────
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

        # ── 2. Upload (100 MB+ dosyalarda multipart da koşar) ─────────────────
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

        # ── 3. Download ───────────────────────────────────────────────────────
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

        # ── 4. Metadata: ListObjectsV2 + HeadObject ───────────────────────────
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
        # Hata olsa bile izleyiciyi kapat, yoksa arka planda çalışmaya devam eder
        resource_monitor.durdur()

    metrics.set_status("Tamamlandı")
    logging.info("Benchmark tamamlandı: prefix=%s", test_prefix)
    return _sonuc_topla(resource_monitor.get_data())


def _sonuc_topla(res_data=None):
    """Metrikleri toplar, özet çıkarır ve upload/download için ayrı tablolar hazırlar."""
    if res_data is None:
        res_data = []
    sonuclar = metrics.tum_sonuclari_al()
    df = reporter.tabloya_cevir(sonuclar)
    ozet = reporter.ozet_cikar(df)

    if df.empty:
        return df, ozet, df.copy(), df.copy(), res_data

    upload_df = _filtrele_ve_mb(df, "upload")
    download_df = _filtrele_ve_mb(df, "download")
    return df, ozet, upload_df, download_df, res_data


def _filtrele_ve_mb(df, islem_tipi):
    """Belirtilen işlem tipini ayırır, boyutu bayttan MB'a çevirir."""
    alt = df[df["islem_tipi"] == islem_tipi].copy()
    if "boyut_byte" in alt.columns:
        alt["boyut_mb"] = alt["boyut_byte"] / (1024 * 1024)
        alt = alt.drop(columns=["boyut_byte"])
    return alt


def _bos_sonuc():
    df = pd.DataFrame()
    return df, reporter.ozet_cikar(df), df.copy(), df.copy(), []


def _isinma_evresi_calistir(endpoint, access_key, secret_key, bucket_name, prefix):
    """
    Asıl test öncesi sistemi ısıtır.

    3 adet 1MB dosya yükleyip indirip siler.
    Bittikten sonra sayaçları temizler; ısınma verileri sonuçlara girmez.
    """
    metrics.set_status("Isınma Evresi Çalışıyor... (Disk ve Ağ Isıtılıyor)")
    logging.info("Isınma evresi başlatılıyor...")

    generator.generate_files(
        folder_path="warmup_files",
        file_count=3,
        file_size_min_mb=1.0,
        file_size_max_mb=1.0,
    )

    uploader.upload_files(
        folder_path="warmup_files",
        bucket_name=bucket_name,
        endpoint_url=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        concurrency=3,
        prefix=prefix,
    )

    downloader.download_files(
        bucket_name=bucket_name,
        endpoint_url=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        indirilecek_klasor="warmup_downloaded",
        concurrency=3,
        prefix=prefix,
    )

    # Geçici dosyaları S3'ten temizle
    from core import s3_utils
    s3_utils.delete_prefix(bucket_name, prefix, endpoint, access_key, secret_key)

    # Sayaçları sıfırla; buraya kadar olan veriler ana teste karışmasın
    metrics.kuyrugu_temizle()
    logging.info("Isınma evresi tamamlandı, sayaçlar sıfırlandı.")
