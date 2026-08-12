"""
metadata_ops.py — ListObjectsV2 ve HeadObject performans ölçümü.

Test akışında Upload/Download aşamasından sonra çalışır.
Sonuçlar metrics modülüne 'list_objects' ve 'head_object' tipleriyle yazılır.
"""
import time
import logging
from concurrent.futures import ThreadPoolExecutor

import boto3
from boto3.session import Config

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
        ),
    )


def benchmark_list_objects(
    bucket_name: str,
    endpoint_url: str,
    access_key: str,
    secret_key: str,
    prefix: str | None = None,
    tekrar: int = 10,
) -> None:
    """
    ListObjectsV2 isteğini `tekrar` kez çalıştırarak her seferinin
    latency'sini ölçer ve metrics'e 'list_objects' tipiyle yazar.

    Parameters
    ----------
    tekrar : Her benchmark turunda kaç kez list_objects çağrısı yapılacak
    """
    metrics.set_status("Metadata benchmark (ListObjectsV2) yapılıyor…")
    s3 = _s3_client(endpoint_url, access_key, secret_key)
    kwargs = {"Bucket": bucket_name}
    if prefix:
        kwargs["Prefix"] = prefix if prefix.endswith("/") else f"{prefix}/"

    for i in range(tekrar):
        t0 = time.perf_counter()
        try:
            s3.list_objects_v2(**kwargs)
            basarili = True
        except Exception as e:
            basarili = False
            logging.exception("ListObjectsV2 hatası (tur %d): %s", i + 1, e)
        sure = time.perf_counter() - t0

        # boyut_byte=None çünkü bu bir metadata işlemi, veri transferi yok
        metrics.kaydet(
            dosya_adi=f"list_tur_{i + 1}",
            sure=sure,
            basarili=basarili,
            islem_tipi="list_objects",
            boyut_byte=None,
        )
        logging.info("ListObjectsV2 tur %d: %.4f sn", i + 1, sure)

    metrics.set_status("Metadata benchmark (ListObjectsV2) tamamlandı")


def benchmark_head_object(
    bucket_name: str,
    endpoint_url: str,
    access_key: str,
    secret_key: str,
    prefix: str | None = None,
    concurrency: int = 4,
) -> None:
    """
    Bucket içindeki her nesne için HeadObject isteği atar ve
    latency'yi ölçer. Sonuçlar 'head_object' tipiyle kaydedilir.
    """
    metrics.set_status("Metadata benchmark (HeadObject) yapılıyor…")
    s3 = _s3_client(endpoint_url, access_key, secret_key)

    # Hangi nesnelerin üzerinde HeadObject çalışacağını listele
    list_kwargs = {"Bucket": bucket_name}
    if prefix:
        list_kwargs["Prefix"] = prefix if prefix.endswith("/") else f"{prefix}/"

    response = s3.list_objects_v2(**list_kwargs)
    anahtarlar = []
    if "Contents" in response:
        for obj in response["Contents"]:
            # _mp kopyalarını ve ana dosyaları ayrı ayrı benchmark et
            anahtarlar.append(obj["Key"])

    if not anahtarlar:
        logging.warning("HeadObject için hiç nesne bulunamadı (prefix=%s)", prefix)
        return

    def _head_one(key: str) -> None:
        t0 = time.perf_counter()
        try:
            s3.head_object(Bucket=bucket_name, Key=key)
            basarili = True
        except Exception as e:
            basarili = False
            logging.exception("HeadObject hatası (%s): %s", key, e)
        sure = time.perf_counter() - t0

        metrics.kaydet(
            dosya_adi=key,
            sure=sure,
            basarili=basarili,
            islem_tipi="head_object",
            boyut_byte=None,
        )
        logging.info("HeadObject: %s, süre: %.4f sn", key, sure)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        for key in anahtarlar:
            executor.submit(_head_one, key)

    metrics.set_status("Metadata benchmark (HeadObject) tamamlandı")
