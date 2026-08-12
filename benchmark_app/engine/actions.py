"""
actions.py — Benchmark orkestrasyonu.

Standart akış:
  1. Dosya üretimi (generator)
  2. Upload + Multipart Upload (uploader)
  3. Download (downloader)
  4. Metadata benchmark — ListObjectsV2 + HeadObject (metadata_ops)

Karma İş Yükü akışı:
  1. Dosya üretimi
  2. Setup Upload (nesne havuzu — metriklere dahil edilmez)
  3. Kaynak izleyici başlatılır (analytics/resource_monitor)
  4. Karma benchmark çalışır (engine/mixed_engine)
  5. Kaynak izleyici durdurulur

Delete (deleter) her iki akış için de ayrı kullanıcı aksiyonuyla tetiklenir.
"""
import logging

import boto3
from boto3.session import Config

from core import generator, uploader, downloader, metadata_ops
from analytics import metrics, reporter, resource_monitor
from engine import mixed_engine


# ─────────────────────────────────────────────────────────────────────────────
# Standart Benchmark
# ─────────────────────────────────────────────────────────────────────────────

def run_benchmark(
    ayarlar,
    endpoint,
    access_key,
    secret_key,
    bucket_name,
    test_prefix,
    folder_path="generated_files",
    indirilecek_klasor="downloaded_files",
    iptal_kontrol=None,
):
    """
    Tam standart benchmark akışını çalıştırır.

    Returns
    -------
    tuple : (df, ozet, upload_df, download_df)
    """
    metrics.kuyrugu_temizle()

    logging.info(
        "Benchmark başlatılıyor: prefix=%s, file_count=%s",
        test_prefix,
        ayarlar.get("file_count"),
    )

    # ── Adım 1: Dosya Üretimi ────────────────────────────────────────────────
    metrics.set_status("Dosyalar üretiliyor…")
    generator.generate_files(
        folder_path=folder_path,
        file_count=ayarlar["file_count"],
        file_size_min_mb=ayarlar["file_size_min_mb"],
        file_size_max_mb=ayarlar["file_size_max_mb"],
    )

    if iptal_kontrol and iptal_kontrol():
        logging.info("Benchmark iptal edildi (dosya üretiminden sonra).")
        return _bos_sonuc()

    # ── Adım 2: Upload (+ Multipart kıyaslaması) ─────────────────────────────
    uploader.upload_files(
        folder_path=folder_path,
        bucket_name=bucket_name,
        endpoint_url=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        concurrency=ayarlar.get("concurrency", 4),
        prefix=test_prefix,
        iptal_kontrol=iptal_kontrol,
    )

    if iptal_kontrol and iptal_kontrol():
        logging.info("Benchmark iptal edildi (upload sonrası).")
        return _sonuc_topla()

    # ── Adım 3: Download ─────────────────────────────────────────────────────
    downloader.download_files(
        bucket_name=bucket_name,
        endpoint_url=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        indirilecek_klasor=indirilecek_klasor,
        concurrency=ayarlar.get("concurrency", 4),
        prefix=test_prefix,
        iptal_kontrol=iptal_kontrol,
    )

    if iptal_kontrol and iptal_kontrol():
        logging.info("Benchmark iptal edildi (download sonrası).")
        return _sonuc_topla()

    # ── Adım 4: Metadata benchmark — List + Head ─────────────────────────────
    metadata_ops.benchmark_list_objects(
        bucket_name=bucket_name,
        endpoint_url=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        prefix=test_prefix,
        tekrar=10,
    )

    if not (iptal_kontrol and iptal_kontrol()):
        metadata_ops.benchmark_head_object(
            bucket_name=bucket_name,
            endpoint_url=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            prefix=test_prefix,
            concurrency=ayarlar.get("concurrency", 4),
        )

    metrics.set_status("Tamamlandı")
    logging.info("Benchmark tamamlandı: prefix=%s", test_prefix)
    return _sonuc_topla()


# ─────────────────────────────────────────────────────────────────────────────
# Karma İş Yükü Benchmark
# ─────────────────────────────────────────────────────────────────────────────

def run_mixed_benchmark(
    ayarlar,
    endpoint,
    access_key,
    secret_key,
    bucket_name,
    test_prefix,
    karma_ayarlar,
    folder_path="generated_files",
    iptal_kontrol=None,
):
    """
    Karma İş Yükü benchmark akışını çalıştırır.

    Parameters
    ----------
    karma_ayarlar : dict
        {
            "sure_sn"          : float  (karma faz süresi, örn. 60)
            "upload_agirlik"   : int    (örn. 20)
            "download_agirlik" : int    (örn. 70)
            "head_agirlik"     : int    (örn. 10)
        }

    Returns
    -------
    tuple : (df, ozet, resource_data)
        resource_data: list[dict] — CPU/RAM/Ağ anlık görüntüleri
    """
    metrics.kuyrugu_temizle()
    resource_monitor.temizle()

    logging.info(
        "Karma benchmark başlatılıyor: prefix=%s, süre=%ss",
        test_prefix,
        karma_ayarlar.get("sure_sn", 60),
    )

    # ── Adım 1: Dosya üretimi ────────────────────────────────────────────────
    metrics.set_status("Dosyalar üretiliyor…")
    generator.generate_files(
        folder_path=folder_path,
        file_count=ayarlar["file_count"],
        file_size_min_mb=ayarlar["file_size_min_mb"],
        file_size_max_mb=ayarlar["file_size_max_mb"],
    )

    if iptal_kontrol and iptal_kontrol():
        return _karma_bos_sonuc()

    # ── Adım 2: Setup upload — nesne havuzu oluştur (metriklere dahil değil) ─
    metrics.set_status("Nesne havuzu hazırlanıyor (setup upload)…")
    uploader.upload_files(
        folder_path=folder_path,
        bucket_name=bucket_name,
        endpoint_url=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        concurrency=ayarlar.get("concurrency", 4),
        prefix=test_prefix,
        iptal_kontrol=iptal_kontrol,
    )

    if iptal_kontrol and iptal_kontrol():
        return _karma_bos_sonuc()

    # Setup upload metriklerini temizle — sadece karma fazını ölç
    metrics.kuyrugu_temizle()

    # ── Adım 3: Mevcut nesne anahtarlarını listele ───────────────────────────
    metrics.set_status("Nesne listesi alınıyor…")
    mevcut_keyler = _prefix_keylerini_listele(
        bucket_name, endpoint, access_key, secret_key, test_prefix
    )
    logging.info("Karma benchmark için %d mevcut nesne hazır.", len(mevcut_keyler))

    # ── Adım 4: Kaynak izleyiciyi başlat ─────────────────────────────────────
    resource_monitor.baslat(aralik_sn=0.5)

    # ── Adım 5: Karma iş yükü motoru ─────────────────────────────────────────
    try:
        mixed_engine.run_mixed_benchmark(
            bucket_name=bucket_name,
            endpoint_url=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            prefix=test_prefix,
            mevcut_keyler=mevcut_keyler,
            yukleme_klasoru=folder_path,
            sure_sn=karma_ayarlar.get("sure_sn", 60),
            concurrency=ayarlar.get("concurrency", 4),
            upload_agirlik=karma_ayarlar.get("upload_agirlik", 20),
            download_agirlik=karma_ayarlar.get("download_agirlik", 70),
            head_agirlik=karma_ayarlar.get("head_agirlik", 10),
            iptal_kontrol=iptal_kontrol,
        )
    finally:
        # ── Adım 6: Kaynak izleyiciyi durdur (hata olsa bile) ────────────────
        resource_monitor.durdur()

    resource_data = resource_monitor.get_data()
    sonuclar = metrics.tum_sonuclari_al()
    df = reporter.tabloya_cevir(sonuclar)
    ozet = reporter.ozet_cikar(df)

    metrics.set_status("Karma benchmark tamamlandı")
    logging.info("Karma benchmark tamamlandı: prefix=%s", test_prefix)
    return df, ozet, resource_data


# ─────────────────────────────────────────────────────────────────────────────
# Yardımcı Fonksiyonlar
# ─────────────────────────────────────────────────────────────────────────────

def _prefix_keylerini_listele(
    bucket_name: str,
    endpoint_url: str,
    access_key: str,
    secret_key: str,
    prefix: str,
) -> list:
    """Belirtilen prefix altındaki tüm nesne anahtarlarını döndürür."""
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
            max_pool_connections=10,
        ),
    )
    prefix_tam = prefix if prefix.endswith("/") else f"{prefix}/"
    anahtarlar = []
    kwargs = {"Bucket": bucket_name, "Prefix": prefix_tam}
    while True:
        resp = s3.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            # _mp kopyalarını hariç tut
            if not obj["Key"].endswith("_mp"):
                anahtarlar.append(obj["Key"])
        if not resp.get("IsTruncated"):
            break
        kwargs["ContinuationToken"] = resp.get("NextContinuationToken")
    return anahtarlar


def _bos_sonuc():
    import pandas as pd
    df = pd.DataFrame()
    return df, reporter.ozet_cikar(df), df.copy(), df.copy()


def _karma_bos_sonuc():
    import pandas as pd
    df = pd.DataFrame()
    return df, reporter.ozet_cikar(df), []


def _sonuc_topla():
    """Toplanan metrikleri reporter'dan geçirir ve standart tuple döndürür."""
    sonuclar = metrics.tum_sonuclari_al()
    df = reporter.tabloya_cevir(sonuclar)
    ozet = reporter.ozet_cikar(df)

    if df.empty:
        return df, ozet, df.copy(), df.copy()

    upload_df = _filtrele_ve_mb(df, "upload")
    download_df = _filtrele_ve_mb(df, "download")
    return df, ozet, upload_df, download_df


def _filtrele_ve_mb(df, islem_tipi):
    """Verilen işlem tipini filtreler ve boyut_byte sütununu MB'a çevirir."""
    alt = df[df["islem_tipi"] == islem_tipi].copy()
    if "boyut_byte" in alt.columns:
        alt["boyut_mb"] = alt["boyut_byte"] / (1024 * 1024)
        alt = alt.drop(columns=["boyut_byte"])
    return alt