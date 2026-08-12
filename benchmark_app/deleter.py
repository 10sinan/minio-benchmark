"""
deleter.py — DeleteObjects (toplu silme) performans benchmarkı.

Kullanıcı isteğiyle çalışır (otomatik değil).
Belirtilen prefix altındaki tüm nesneleri 1000'lik paketler halinde
siler ve silme hızını (ops/sn) ölçer.

MinIO / Türkcell Bulut gibi S3 uyumlu sunucuların DeleteObjects için
zorunlu kıldığı 'Content-MD5' başlığı otomatik hesaplanarak eklenir.
"""
import base64
import hashlib
import time
import logging
from concurrent.futures import ThreadPoolExecutor

import boto3
from boto3.session import Config

import metrics


def _add_content_md5(request, **kwargs):
    """
    DeleteObjects isteğinin body'si için Content-MD5 başlığını hesaplar ve ekler.
    MinIO sunucularının 'Missing required header: Content-MD5' hatasını önler.
    """
    if request.body:
        if isinstance(request.body, str):
            body_bytes = request.body.encode("utf-8")
        else:
            body_bytes = request.body
        md5_digest = hashlib.md5(body_bytes).digest()
        md5_b64 = base64.b64encode(md5_digest).decode("utf-8")
        request.headers["Content-MD5"] = md5_b64


def _s3_client(endpoint_url, access_key, secret_key):
    s3 = boto3.client(
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
    s3.meta.events.register("before-sign.s3.DeleteObjects", _add_content_md5)
    return s3


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
        basarili_bu_batch = 0
        try:
            resp = s3.delete_objects(Bucket=bucket_name, Delete=delete_payload)
            if "Errors" in resp and resp["Errors"]:
                logging.error("DeleteObjects kısmi hata (batch %d): %s", i // batch_size + 1, resp["Errors"])
            basarili_bu_batch = len(resp.get("Deleted", []))
            # Eğer deleted boş dönerse ancak error yoksa (quiet mode vb.), hepsini başarılı say
            if basarili_bu_batch == 0 and not resp.get("Errors"):
                basarili_bu_batch = len(batch)
        except Exception as e:
            logging.exception("DeleteObjects toplu silme hatası (batch %d): %s. Tek tek silme deneniyor…", i // batch_size + 1, e)
            # Fallback: Toplu silme hata verirse tek tek silmeyi dene
            basarili_bu_batch = _fallback_delete_single(s3, bucket_name, batch)

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
            "DeleteObjects batch %d/%d: %d/%d nesne silindi, süre=%.4f sn",
            i // batch_size + 1,
            -(-toplam_nesne // batch_size),  # ceil division
            basarili_bu_batch,
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


def _fallback_delete_single(s3, bucket_name, batch_keys):
    """DeleteObjects başarısız olursa nesneleri tek tek sileyim der."""
    silinen = 0

    def _delete_one(key):
        nonlocal silinen
        try:
            s3.delete_object(Bucket=bucket_name, Key=key)
            silinen += 1
        except Exception as ex:
            logging.exception("Tekil delete_object hatası (%s): %s", key, ex)

    with ThreadPoolExecutor(max_workers=10) as executor:
        for key in batch_keys:
            executor.submit(_delete_one, key)

    return silinen
