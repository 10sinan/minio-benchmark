import os
import time
import boto3
from concurrent.futures import ThreadPoolExecutor
import metrics


def upload_single_file(s3, folder_path, bucket_name, dosya_adi):
    tam_yol = os.path.join(folder_path, dosya_adi)

    baslangic = time.perf_counter()
    try:
        s3.upload_file(tam_yol, bucket_name, dosya_adi)
        basarili = True
    except Exception as e:
        basarili = False
        print(f"HATA: {dosya_adi} yüklenemedi - {e}")
    bitis = time.perf_counter()

    sure = bitis - baslangic
    metrics.kaydet(dosya_adi, sure, basarili, islem_tipi="upload")
    print(f"Yüklendi: {dosya_adi}, süre: {sure:.4f} saniye")


def upload_files(folder_path, bucket_name, endpoint_url, access_key, secret_key, concurrency=4):
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )

    dosyalar = os.listdir(folder_path)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        for dosya_adi in dosyalar:
            executor.submit(upload_single_file, s3, folder_path, bucket_name, dosya_adi)


if __name__ == "__main__":
    upload_files(
        folder_path="generated_files",
        bucket_name="test-bucket",
        endpoint_url="http://localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin"
    )