"""
downloader.py

S3'teki dosyaları paralel olarak indirir ve her işlemin süresini kaydeder.
"""
import os
import time
import logging
import boto3
from boto3.session import Config
from concurrent.futures import ThreadPoolExecutor

from analytics import metrics


def _s3_client(endpoint_url, access_key, secret_key):
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
            max_pool_connections=50,
            retries={"max_attempts": 5, "mode": "adaptive"},
        ),
    )


def download_single_file(s3, bucket_name, dosya_adi, indirilecek_klasor, boyut_byte=None):
    local_name = os.path.basename(dosya_adi)
    tam_yol = os.path.join(indirilecek_klasor, local_name)

    baslangic = time.perf_counter()
    try:
        s3.download_file(bucket_name, dosya_adi, tam_yol)
        basarili = True
    except Exception as e:
        basarili = False
        logging.exception("HATA: %s indirilemedi - %s", dosya_adi, e)
    bitis = time.perf_counter()

    sure = bitis - baslangic
    metrics.kaydet(dosya_adi, sure, basarili, islem_tipi="download", boyut_byte=boyut_byte)
    logging.info("İndirildi: %s, süre: %.4f saniye", dosya_adi, sure)


def download_files(
    bucket_name,
    endpoint_url,
    access_key,
    secret_key,
    indirilecek_klasor,
    concurrency=4,
    prefix=None,
    iptal_kontrol=None,
):
    metrics.set_status("Download yapılıyor…")
    s3 = _s3_client(endpoint_url, access_key, secret_key)
    os.makedirs(indirilecek_klasor, exist_ok=True)

    list_kwargs = {"Bucket": bucket_name}
    if prefix:
        list_kwargs["Prefix"] = prefix if prefix.endswith("/") else f"{prefix}/"

    response = s3.list_objects_v2(**list_kwargs)
    dosyalar = []
    if "Contents" in response:
        for obj in response["Contents"]:
            # _mp uzantılı nesneler multipart kopya; indirilmesine gerek yok
            if not obj["Key"].endswith("_mp"):
                dosyalar.append({"key": obj["Key"], "boyut_byte": obj["Size"]})

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        for dosya in dosyalar:
            if iptal_kontrol and iptal_kontrol():
                logging.info("İndirme iptal edildi, kalan dosyalar atlanıyor.")
                break
            executor.submit(
                download_single_file,
                s3,
                bucket_name,
                dosya["key"],
                indirilecek_klasor,
                dosya["boyut_byte"],
            )
    metrics.set_status("Download tamamlandı")


def list_files(bucket_name, endpoint_url, access_key, secret_key):
    s3 = _s3_client(endpoint_url, access_key, secret_key)
    response = s3.list_objects_v2(Bucket=bucket_name)
    dosyalar = []
    if "Contents" in response:
        for obj in response["Contents"]:
            dosyalar.append({"dosya_adi": obj["Key"], "boyut_byte": obj["Size"]})
    return dosyalar


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    download_files(
        bucket_name="test-bucket",
        endpoint_url=os.getenv("MINIO_ENDPOINT"),
        access_key=os.getenv("MINIO_ACCESS_KEY"),
        secret_key=os.getenv("MINIO_SECRET_KEY"),
        indirilecek_klasor="downloaded_files",
    )