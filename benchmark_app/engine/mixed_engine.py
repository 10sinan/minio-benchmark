"""
engine/mixed_engine.py — Karma İş Yükü Motoru (Mixed Workload Engine).

Gerçek canlı sunucu trafiğini simüle eder:
aynı anda Upload (karma_upload), Download (karma_download)
ve HeadObject (karma_head) işlemleri ağırlıklı rastgele seçimle akar.

Sonuçlar mevcut metrics modülüne ilgili islem_tipi etiketiyle yazılır.
"""
import os
import time
import random
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

import boto3
from boto3.session import Config

import metrics


def _s3_client(endpoint_url: str, access_key: str, secret_key: str):
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
            max_pool_connections=100,
        ),
    )


def run_mixed_benchmark(
    bucket_name: str,
    endpoint_url: str,
    access_key: str,
    secret_key: str,
    prefix: str,
    mevcut_keyler: list,        # download / head için mevcut nesne anahtarları
    yukleme_klasoru: str,       # upload için yerel dosya klasörü
    sure_sn: float = 60.0,
    concurrency: int = 4,
    upload_agirlik: int = 20,
    download_agirlik: int = 70,
    head_agirlik: int = 10,
    iptal_kontrol=None,
) -> None:
    """
    Belirtilen süre (sure_sn) boyunca ağırlıklı rastgele karma S3 iş yükü çalıştırır.

    Her worker thread kendi döngüsünde çalışır:
    - Ağırlıklara göre rastgele işlem seçer
    - İşlemi gerçekleştirir
    - Süre/başarı metriğini kaydeder
    - Süre dolana veya iptal gelene kadar tekrar eder
    """
    metrics.set_status(f"Karma iş yükü çalışıyor… (süre={sure_sn}sn)")

    s3 = _s3_client(endpoint_url, access_key, secret_key)

    islem_tipleri = ["upload", "download", "head"]
    agirliklar = [upload_agirlik, download_agirlik, head_agirlik]

    bitis_zamani = time.time() + sure_sn

    # Upload dosyaları yerel klasörden hazırla
    upload_dosyalari: list[str] = []
    if yukleme_klasoru and os.path.exists(yukleme_klasoru):
        upload_dosyalari = os.listdir(yukleme_klasoru)

    # Paylaşılan anahtar listesi ve sayaç (thread-safe)
    _kil = threading.Lock()
    _paylaşilan_keyler: list = list(mevcut_keyler)
    _upload_sayaci = {"n": 0}

    # ─── Tek işlem fonksiyonu ──────────────────────────────────────────────────

    def _bir_islem() -> None:
        with _kil:
            mevcut = list(_paylaşilan_keyler)
        # Mevcut nesne yokken download/head anlamsız — sadece upload yap
        if not mevcut:
            aktif = ["upload"]
            aktif_ag = [1]
        else:
            aktif = islem_tipleri
            aktif_ag = agirliklar

        secilen = random.choices(aktif, weights=aktif_ag, k=1)[0]

        # ── karma_upload ───────────────────────────────────────────────────────
        if secilen == "upload":
            if not upload_dosyalari:
                return
            dosya = random.choice(upload_dosyalari)
            tam_yol = os.path.join(yukleme_klasoru, dosya)
            boyut = os.path.getsize(tam_yol)
            with _kil:
                sayac = _upload_sayaci["n"]
                _upload_sayaci["n"] += 1
            key = f"{prefix}/karma_{sayac}_{dosya}"

            t0 = time.perf_counter()
            try:
                s3.upload_file(tam_yol, bucket_name, key)
                basarili = True
                with _kil:
                    _paylaşilan_keyler.append(key)
            except Exception as e:
                basarili = False
                logging.exception("Karma upload hatası (%s): %s", dosya, e)
            sure = time.perf_counter() - t0
            metrics.kaydet(dosya, sure, basarili, "karma_upload", boyut_byte=boyut)

        # ── karma_download ─────────────────────────────────────────────────────
        elif secilen == "download":
            with _kil:
                keyler = list(_paylaşilan_keyler)
            if not keyler:
                return
            key = random.choice(keyler)
            boyut = None
            t0 = time.perf_counter()
            try:
                resp = s3.get_object(Bucket=bucket_name, Key=key)
                data = resp["Body"].read()
                boyut = len(data)
                basarili = True
            except Exception as e:
                basarili = False
                logging.exception("Karma download hatası (%s): %s", key, e)
            sure = time.perf_counter() - t0
            metrics.kaydet(key, sure, basarili, "karma_download", boyut_byte=boyut)

        # ── karma_head ─────────────────────────────────────────────────────────
        elif secilen == "head":
            with _kil:
                keyler = list(_paylaşilan_keyler)
            if not keyler:
                return
            key = random.choice(keyler)
            t0 = time.perf_counter()
            try:
                s3.head_object(Bucket=bucket_name, Key=key)
                basarili = True
            except Exception as e:
                basarili = False
                logging.exception("Karma head hatası (%s): %s", key, e)
            sure = time.perf_counter() - t0
            metrics.kaydet(key, sure, basarili, "karma_head", boyut_byte=None)

    # ─── Worker thread: süre dolana kadar döngüde çalışır ────────────────────

    def _worker():
        while time.time() < bitis_zamani:
            if iptal_kontrol and iptal_kontrol():
                break
            _bir_islem()

    # ─── Thread havuzu ────────────────────────────────────────────────────────
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(_worker) for _ in range(concurrency)]
        for f in futures:
            try:
                f.result()
            except Exception as e:
                logging.exception("Karma worker istisnası: %s", e)

    toplam = len(metrics.tum_sonuclari_al())
    logging.info("Karma iş yükü tamamlandı. Toplam %d işlem kaydedildi.", toplam)
    metrics.set_status("Karma iş yükü tamamlandı")
