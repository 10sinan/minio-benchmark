"""
engine/actions.py — Benchmark Orkestrasyon Katmanı.

Bu modül, alt motorları (standard_engine, mixed_engine) tek bir arayüz
altında toplar. Dışarıdan yalnızca bu dosya import edilir.
"""
import logging

from core import generator, uploader
from analytics import metrics, reporter, resource_monitor
from engine.standard_engine import run_benchmark
from engine.mixed_engine import (
    run_mixed_benchmark as _run_mixed_engine,
    _prefix_keylerini_listele,
    _karma_bos_sonuc,
)


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
        _run_mixed_engine(
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


__all__ = [
    "run_benchmark",
    "run_mixed_benchmark",
]