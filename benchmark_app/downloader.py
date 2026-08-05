import os
import time
import boto3
from boto3.session import Config
from concurrent.futures import ThreadPoolExecutor
import metrics


def download_single_file(s3, bucket_name, dosya_adi, indirilecek_klasor, boyut_byte=None):
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
    metrics.kaydet(dosya_adi, sure, basarili, islem_tipi="download", boyut_byte=boyut_byte)
    print(f"İndirildi: {dosya_adi}, süre: {sure:.4f} saniye")


def download_files(bucket_name, endpoint_url, access_key, secret_key, indirilecek_klasor, concurrency=4):
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required"
        )
)

    os.makedirs(indirilecek_klasor, exist_ok=True)

    response = s3.list_objects_v2(Bucket=bucket_name)
    dosyalar = []
    for obj in response["Contents"]:
        dosyalar.append({"key": obj["Key"], "boyut_byte": obj["Size"]})

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        for dosya in dosyalar:
            executor.submit(
                download_single_file,
                s3,
                bucket_name,
                dosya["key"],
                indirilecek_klasor,
                dosya["boyut_byte"],
            )



def list_files(bucket_name, endpoint_url, access_key, secret_key):
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required"
        )
    )

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