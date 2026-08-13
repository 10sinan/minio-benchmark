"""
uploader.py

Dosyaları S3'e paralel olarak yükler.
100 MB ve üzeri dosyalar için hem standart PutObject hem de Multipart Upload
çalıştırılır; ikisi de ayrı ayrı ölçülür.
"""
import os
import time
import logging
import boto3
from boto3.session import Config
from boto3.s3.transfer import TransferConfig
from concurrent.futures import ThreadPoolExecutor

from analytics import metrics

# 100 MB üstü dosyalar için multipart da çalışır
MULTIPART_ESIK_BYTE = 100 * 1024 * 1024

# Her multipart parçasının boyutu: 8 MB
MULTIPART_PARCA_BYTE = 8 * 1024 * 1024


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


def upload_single_file(s3, folder_path, bucket_name, dosya_adi, prefix=None):
    """
    Tek bir dosyayı yükler ve süreyi kaydeder.
    100 MB+ dosyalar için ek olarak Multipart Upload da yapılır (kıyaslama amaçlı).
    """
    tam_yol = os.path.join(folder_path, dosya_adi)
    boyut_byte = os.path.getsize(tam_yol)
    key = f"{prefix}/{dosya_adi}" if prefix else dosya_adi

    # ── Standart PutObject ────────────────────────────────────────────────────
    # Eşiği 5 GB'a çekerek boto3'ün otomatik multipart'ını devre dışı bırakıyoruz;
    # böylece bu çağrı her zaman tek parça PutObject gönderir
    cfg_tek = TransferConfig(
        multipart_threshold=5 * 1024 * 1024 * 1024,
        use_threads=False,
    )
    t0 = time.perf_counter()
    try:
        s3.upload_file(tam_yol, bucket_name, key, Config=cfg_tek)
        basarili = True
    except Exception as e:
        basarili = False
        logging.exception("HATA (PutObject): %s yüklenemedi - %s", dosya_adi, e)
    sure_tek = time.perf_counter() - t0

    metrics.kaydet(
        dosya_adi=dosya_adi,
        sure=sure_tek,
        basarili=basarili,
        islem_tipi="upload",
        boyut_byte=boyut_byte,
    )
    logging.info("PutObject: %s (prefix=%s), süre: %.4f sn", dosya_adi, prefix, sure_tek)

    # ── Multipart Upload (yalnızca 100 MB+ dosyalar için) ─────────────────────
    if boyut_byte >= MULTIPART_ESIK_BYTE:
        key_mp = f"{key}_mp"
        cfg_mp = TransferConfig(
            multipart_threshold=MULTIPART_PARCA_BYTE,
            multipart_chunksize=MULTIPART_PARCA_BYTE,
            use_threads=True,
            max_concurrency=4,
        )
        t1 = time.perf_counter()
        try:
            s3.upload_file(tam_yol, bucket_name, key_mp, Config=cfg_mp)
            mp_basarili = True
        except Exception as e:
            mp_basarili = False
            logging.exception("HATA (Multipart): %s yüklenemedi - %s", dosya_adi, e)
        sure_mp = time.perf_counter() - t1

        metrics.kaydet(
            dosya_adi=dosya_adi,
            sure=sure_mp,
            basarili=mp_basarili,
            islem_tipi="multipart_upload",
            boyut_byte=boyut_byte,
        )
        logging.info(
            "Multipart: %s (prefix=%s), süre: %.4f sn", dosya_adi, prefix, sure_mp
        )


def upload_files(
    folder_path,
    bucket_name,
    endpoint_url,
    access_key,
    secret_key,
    concurrency=4,
    prefix=None,
    iptal_kontrol=None,
):
    metrics.set_status("Upload yapılıyor…")
    s3 = _s3_client(endpoint_url, access_key, secret_key)
    dosyalar = os.listdir(folder_path)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        for dosya_adi in dosyalar:
            if iptal_kontrol and iptal_kontrol():
                logging.info("Yükleme iptal edildi, kalan dosyalar atlanıyor.")
                break
            executor.submit(
                upload_single_file, s3, folder_path, bucket_name, dosya_adi, prefix
            )
    metrics.set_status("Upload tamamlandı")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    upload_files(
        folder_path="generated_files",
        bucket_name="test-bucket",
        endpoint_url=os.getenv("MINIO_ENDPOINT"),
        access_key=os.getenv("MINIO_ACCESS_KEY"),
        secret_key=os.getenv("MINIO_SECRET_KEY"),
    )