"""
history.py — Test geçmişini test_gecmisi.csv dosyasına kaydeder.

Yeni sütunlar: test_id, test_adi, p95, p99, multipart_upload_throughput_mb_s,
               list_objects_ops_per_sec, head_object_ops_per_sec,
               delete_ops_per_sec
"""
import os
import csv
import uuid
from datetime import datetime

GECMIS_DOSYA = "test_gecmisi.csv"

SUTUNLAR = [
    "test_id",
    "test_adi",
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


def kaydet(profil_adi, bucket_name, ozet, test_adi=""):
    dosya_var_mi = os.path.exists(GECMIS_DOSYA)
    
    tarih_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    test_id = str(uuid.uuid4())
    
    if not test_adi:
        test_adi = f"Test ({tarih_str})"

    with open(GECMIS_DOSYA, "a", newline="", encoding="utf-8") as f:
        yazici = csv.writer(f)

        if not dosya_var_mi:
            yazici.writerow(SUTUNLAR)

        yazici.writerow(
            [
                test_id,
                test_adi,
                tarih_str,
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
    try:
        df = pd.read_csv(GECMIS_DOSYA)
        
        # Geriye dönük uyumluluk: eski csv formatı için
        degisti = False
        if "test_id" not in df.columns:
            df["test_id"] = [str(uuid.uuid4()) for _ in range(len(df))]
            degisti = True
        if "test_adi" not in df.columns:
            if "tarih" in df.columns:
                df["test_adi"] = "Test (" + df["tarih"].astype(str) + ")"
            else:
                df["test_adi"] = "Bilinmeyen Test"
            degisti = True
            
        # Eksik sütunları SUTUNLAR sırasına göre düzenle
        for sutun in SUTUNLAR:
            if sutun not in df.columns:
                df[sutun] = ""
                
        # Sadece SUTUNLAR listesindeki sütunları ve sırasını al
        df = df[SUTUNLAR]
        
        if degisti:
            # Eski dosyayı yeni formatta kaydet
            df.to_csv(GECMIS_DOSYA, index=False, encoding="utf-8")
            
        return df
    except Exception as e:
        print(f"Geçmiş okuma hatası: {e}")
        return None


def isim_guncelle(test_id, yeni_isim):
    df = gecmisi_oku()
    if df is not None:
        mask = df["test_id"] == test_id
        if mask.any():
            df.loc[mask, "test_adi"] = yeni_isim
            # SUTUNLAR listesindeki sıraya uygun olduğundan emin ol (gecmisi_oku zaten hallediyor ama yine de df kullanılıyor)
            df.to_csv(GECMIS_DOSYA, index=False, encoding="utf-8")
            return True
    return False