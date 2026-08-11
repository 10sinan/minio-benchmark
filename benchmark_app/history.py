"""
history.py — Test geçmişini test_gecmisi.csv dosyasına kaydeder.

Yeni sütunlar: p95, p99, multipart_upload_throughput_mb_s,
               list_objects_ops_per_sec, head_object_ops_per_sec,
               delete_ops_per_sec
"""
import os
import csv
from datetime import datetime

GECMIS_DOSYA = "test_gecmisi.csv"

SUTUNLAR = [
    "tarih",
    "profil",
    "bucket",
    "toplam_dosya",
    "basarili",
    "hatali",
    "ortalama_sure",
    "en_hizli",
    "en_yavas",
    "p95",
    "p99",
    "toplam_throughput_mb_s",
    "upload_throughput_mb_s",
    "download_throughput_mb_s",
    "multipart_upload_throughput_mb_s",
    "list_objects_ops_per_sec",
    "head_object_ops_per_sec",
    "delete_ops_per_sec",
]


def kaydet(profil_adi, bucket_name, ozet):
    dosya_var_mi = os.path.exists(GECMIS_DOSYA)

    with open(GECMIS_DOSYA, "a", newline="", encoding="utf-8") as f:
        yazici = csv.writer(f)

        if not dosya_var_mi:
            yazici.writerow(SUTUNLAR)

        yazici.writerow(
            [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                profil_adi,
                bucket_name,
                ozet.get("toplam_dosya", ""),
                ozet.get("basarili", ""),
                ozet.get("hatali", ""),
                f"{ozet.get('ortalama_sure', 0):.4f}",
                f"{ozet.get('en_hizli', 0):.4f}",
                f"{ozet.get('en_yavas', 0):.4f}",
                f"{ozet.get('p95', 0):.4f}",
                f"{ozet.get('p99', 0):.4f}",
                f"{ozet.get('toplam_throughput_mb_s', 0):.2f}",
                f"{ozet.get('upload_throughput_mb_s', 0):.2f}",
                f"{ozet.get('download_throughput_mb_s', 0):.2f}",
                f"{ozet.get('multipart_upload_throughput_mb_s', 0):.2f}",
                f"{ozet.get('list_objects_ops_per_sec', 0):.2f}",
                f"{ozet.get('head_object_ops_per_sec', 0):.2f}",
                f"{ozet.get('delete_ops_per_sec', 0):.2f}",
            ]
        )


def gecmisi_oku():
    if not os.path.exists(GECMIS_DOSYA):
        return None

    import pandas as pd
    return pd.read_csv(GECMIS_DOSYA)