import logging
import generator
import uploader
import downloader
import metrics
import reporter

def run_benchmark(ayarlar, endpoint, access_key, secret_key, bucket_name, test_prefix,
                  folder_path="generated_files", indirilecek_klasor="downloaded_files",
                  iptal_kontrol=None):
    
    # Eski metrikleri temizle
    metrics.kuyrugu_temizle()
    
    logging.info("Benchmark başlatılıyor: prefix=%s, file_count=%s", test_prefix, ayarlar.get("file_count"))

    generator.generate_files(
        folder_path=folder_path,
        file_count=ayarlar["file_count"],
        file_size_min_mb=ayarlar["file_size_min_mb"],
        file_size_max_mb=ayarlar["file_size_max_mb"],
    )

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

    sonuclar = metrics.tum_sonuclari_al()
    df = reporter.tabloya_cevir(sonuclar)
    ozet = reporter.ozet_cikar(df)

    if df.empty:
        upload_df = df.copy()
        download_df = df.copy()
    else:
        upload_df = df[df["islem_tipi"] == "upload"].copy()
        download_df = df[df["islem_tipi"] == "download"].copy()

        if "boyut_byte" in upload_df.columns:
            upload_df["boyut_mb"] = upload_df["boyut_byte"] / (1024 * 1024)
            upload_df = upload_df.drop(columns=["boyut_byte"])

        if "boyut_byte" in download_df.columns:
            download_df["boyut_mb"] = download_df["boyut_byte"] / (1024 * 1024)
            download_df = download_df.drop(columns=["boyut_byte"])

    logging.info("Benchmark tamamlandi: prefix=%s", test_prefix)
    return df, ozet, upload_df, download_df