import os
import time
import boto3
from concurrent.futures import ThreadPoolExecutor
import metrics


def download_single_file(s3, bucket_name, dosya_adi, indirilecek_klasor):
    tam_yol = os.path.join(indirilecek_klasor, dosya_adi)

    baslangic = time.perf_counter()
    try:
        s3.download_file(bucket_name, dosya_adi, tam_yol)
        basarili = True
    except Exception as e:
        basarili = False
        print(f"HATA: {dosya_adi} indirilemedi - {e}")
    bitis = time.perf_counter()

    sure = bitis - baslangic
    metrics.kaydet(dosya_adi, sure, basarili, islem_tipi="download")
    print(f"İndirildi: {dosya_adi}, süre: {sure:.4f} saniye")


def download_files(bucket_name, endpoint_url, access_key, secret_key, indirilecek_klasor, concurrency=4):
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )

    os.makedirs(indirilecek_klasor, exist_ok=True)

    response = s3.list_objects_v2(Bucket=bucket_name)
    dosyalar = []
    for obj in response["Contents"]:
        dosyalar.append(obj["Key"])

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        for dosya_adi in dosyalar:
            executor.submit(download_single_file, s3, bucket_name, dosya_adi, indirilecek_klasor)


if __name__ == "__main__":
    download_files(
        bucket_name="test-bucket",
        endpoint_url="http://localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        indirilecek_klasor="downloaded_files"
    )