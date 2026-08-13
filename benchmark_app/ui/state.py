"""
ui/state.py

Session state başlatma ve tüm benchmark thread fonksiyonları burada.
Her thread, sonucu output_dict üzerinden ana UI'a iletir.
"""

import logging
import re
import threading
import uuid

import streamlit as st

from engine import actions
from core import deleter


# ──────────────────────────────────────────────────────────────────────────────
# Session State
# ──────────────────────────────────────────────────────────────────────────────

def init_state() -> None:
    """Sayfa yüklendiğinde henüz tanımlanmamış session değişkenlerini başlatır."""
    defaults = {
        "iptal_event": threading.Event(),
        "test_calisiyor": False,
        "benchmark_sonuc": None,
        "karma_sonuc": None,
        "sweep_sonuc": None,
        "benchmark_hata": None,
        "benchmark_thread": None,
        "thread_output": {},
        "son_prefix": None,
        "son_mod": "standart",
        # Delete benchmark durumu
        "delete_calisiyor": False,
        "delete_thread": None,
        "delete_output": {},
        "delete_sonuc": None,
        "delete_hata": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ──────────────────────────────────────────────────────────────────────────────
# Thread Fonksiyonları
# ──────────────────────────────────────────────────────────────────────────────

def benchmark_thread_fn(ayarlar, endpoint, access_key, secret_key,
                        bucket_name, test_prefix, matrix_ayarlari, iptal_kontrol, output_dict):
    """Standart testi arka planda çalıştırır; sonucu output_dict'e yazar."""
    try:
        df, ozet, upload_df, download_df, res_data = actions.run_benchmark(
            ayarlar=ayarlar, endpoint=endpoint, access_key=access_key,
            secret_key=secret_key, bucket_name=bucket_name,
            test_prefix=test_prefix, matrix_ayarlari=matrix_ayarlari, iptal_kontrol=iptal_kontrol,
        )
        output_dict["sonuc"] = (df, ozet, upload_df, download_df, res_data)
        output_dict["mod"] = "standart"
    except Exception as e:
        logging.exception("Standart benchmark hatası: %s", e)
        output_dict["hata"] = str(e)


def karma_thread_fn(ayarlar, endpoint, access_key, secret_key,
                    bucket_name, test_prefix, karma_ayarlar, iptal_kontrol, output_dict):
    """Karma iş yükü testini arka planda çalıştırır."""
    try:
        df, ozet, res_data = actions.run_mixed_benchmark(
            ayarlar=ayarlar, endpoint=endpoint, access_key=access_key,
            secret_key=secret_key, bucket_name=bucket_name,
            test_prefix=test_prefix, karma_ayarlar=karma_ayarlar,
            iptal_kontrol=iptal_kontrol,
        )
        output_dict["karma_sonuc"] = (df, ozet, res_data)
        output_dict["mod"] = "karma"
    except Exception as e:
        logging.exception("Karma benchmark hatası: %s", e)
        output_dict["hata"] = str(e)


def sweep_thread_fn(ayarlar, endpoint, access_key, secret_key,
                    bucket_name, test_prefix_base, iptal_kontrol, output_dict):
    """Concurrency sweep testini arka planda çalıştırır."""
    try:
        sweep_df = actions.run_concurrency_sweep(
            ayarlar=ayarlar, endpoint=endpoint, access_key=access_key,
            secret_key=secret_key, bucket_name=bucket_name,
            test_prefix_base=test_prefix_base, iptal_kontrol=iptal_kontrol,
        )
        output_dict["sweep_sonuc"] = sweep_df
        output_dict["mod"] = "sweep"
    except Exception as e:
        logging.exception("Sweep benchmark hatası: %s", e)
        output_dict["hata"] = str(e)


def delete_thread_fn(endpoint, access_key, secret_key, bucket_name, prefix, output_dict):
    """Delete benchmark'ını arka planda çalıştırır."""
    try:
        sonuc = deleter.benchmark_delete(
            bucket_name=bucket_name, endpoint_url=endpoint,
            access_key=access_key, secret_key=secret_key, prefix=prefix,
        )
        output_dict["delete_sonuc"] = sonuc
    except Exception as e:
        logging.exception("Delete benchmark hatası: %s", e)
        output_dict["delete_hata"] = str(e)


# ──────────────────────────────────────────────────────────────────────────────
# Test Prefix Üretici
# ──────────────────────────────────────────────────────────────────────────────

def olustur_test_prefix(test_adi: str) -> str:
    """
    Kullanıcının girdiği test adından S3 uyumlu bir prefix üretir.

    Özel karakterler alt çizgiye dönüşür ve sonuna kısa bir UUID eklenir.
    Test adı boşsa tamamen rastgele bir prefix oluşturulur.
    """
    temiz = re.sub(r"[^a-zA-Z0-9_-]", "_", test_adi.strip()).strip("_") if test_adi and test_adi.strip() else ""
    if temiz:
        return f"{temiz[:24]}_{uuid.uuid4().hex[:6]}"
    return f"test_{uuid.uuid4().hex[:8]}"
