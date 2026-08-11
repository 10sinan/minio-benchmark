"""
deleter.py — DeleteObjects (toplu silme) performans benchmarkı.

Kullanıcı isteğiyle çalışır (otomatik değil).
Belirtilen prefix altındaki tüm nesneleri 1000'lik paketler halinde
siler ve silme hızını (ops/sn) ölçer.
"""
import time
import logging

import boto3
from boto3.session import Config

import metrics


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


def benchmark_delete(
    bucket_name: str,
    endpoint_url: str,
    access_key: str,
    secret_key: str,
    prefix: str | None = None,
) -> dict:
    """
    Prefix altındaki tüm nesneleri DeleteObjects API'siyle toplu siler.
    Silme hızı, başarı sayısı ve toplam süre döndürülür.

    Returns
    -------
    dict : {
        "toplam_nesne": int,
        "basarili_silinen": int,
        "toplam_sure_sn": float,
        "ops_per_sec": float,
    }
    """
    metrics.set_status("Delete benchmark yapılıyor…")
    s3 = _s3_client(endpoint_url, access_key, secret_key)

    # Silinecek nesneleri listele (sayfalı)
    anahtarlar = []
    list_kwargs = {"Bucket": bucket_name}
    if prefix:
        list_kwargs["Prefix"] = prefix if prefix.endswith("/") else f"{prefix}/"

    while True:
        resp = s3.list_objects_v2(**list_kwargs)
        for obj in resp.get("Contents", []):
            anahtarlar.append(obj["Key"])
        if not resp.get("IsTruncated"):
            break
        list_kwargs["ContinuationToken"] = resp.get("NextContinuationToken")

    if not anahtarlar:
        logging.warning("Silinecek nesne bulunamadı (prefix=%s)", prefix)
        metrics.set_status("Delete: Silinecek nesne yok")
        return {
            "toplam_nesne": 0,
            "basarili_silinen": 0,
            "toplam_sure_sn": 0.0,
            "ops_per_sec": 0.0,
        }

    toplam_nesne = len(anahtarlar)
    basarili_silinen = 0
    batch_size = 1000  # AWS/MinIO sınırı

    # Toplu silme — tüm paketlerin toplam süresini ölçüyoruz
    genel_baslangic = time.perf_counter()

    for i in range(0, toplam_nesne, batch_size):
        batch = anahtarlar[i : i + batch_size]
        delete_payload = {"Objects": [{"Key": k} for k in batch], "Quiet": False}

        batch_t0 = time.perf_counter()
        try:
            resp = s3.delete_objects(Bucket=bucket_name, Delete=delete_payload)
            basarili_bu_batch = len(batch) - len(resp.get("Errors", []))
        except Exception as e:
            basarili_bu_batch = 0
            logging.exception("DeleteObjects hatası (batch %d): %s", i // batch_size + 1, e)
        batch_sure = time.perf_counter() - batch_t0

        basarili_silinen += basarili_bu_batch

        # Her batch'i ayrı bir metrik olarak kaydet
        metrics.kaydet(
            dosya_adi=f"delete_batch_{i // batch_size + 1}",
            sure=batch_sure,
            basarili=(basarili_bu_batch == len(batch)),
            islem_tipi="delete",
            boyut_byte=None,
        )
        logging.info(
            "DeleteObjects batch %d/%d: %d nesne, süre=%.4f sn",
            i // batch_size + 1,
            -(-toplam_nesne // batch_size),  # ceil division
            len(batch),
            batch_sure,
        )

    toplam_sure = time.perf_counter() - genel_baslangic
    ops_per_sec = basarili_silinen / toplam_sure if toplam_sure > 0 else 0.0

    logging.info(
        "Delete tamamlandı: %d/%d nesne silindi, toplam süre=%.4f sn, hız=%.2f ops/sn",
        basarili_silinen,
        toplam_nesne,
        toplam_sure,
        ops_per_sec,
    )
    metrics.set_status("Delete benchmark tamamlandı")

    return {
        "toplam_nesne": toplam_nesne,
        "basarili_silinen": basarili_silinen,
        "toplam_sure_sn": toplam_sure,
        "ops_per_sec": ops_per_sec,
    }
