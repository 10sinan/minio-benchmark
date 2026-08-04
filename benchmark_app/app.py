import streamlit as st
import yaml
import os
from dotenv import load_dotenv

import generator
import uploader
import downloader
import metrics
import reporter

load_dotenv()

st.title("MinIO Benchmark Aracı")

with open("config.yaml", "r") as f:
    settings = yaml.safe_load(f)

profil_isimleri = list(settings["profiles"].keys())
secilen_profil = st.selectbox("Profil seç", profil_isimleri)

if st.button("Başlat"):
    ayarlar = settings["profiles"][secilen_profil]
    bucket_name = settings["bucket_name"]

    with st.spinner("Dosyalar üretiliyor..."):
        generator.generate_files(
            folder_path="generated_files",
            file_count=ayarlar["file_count"],
            file_size_min_mb=ayarlar["file_size_min_mb"],
            file_size_max_mb=ayarlar["file_size_max_mb"]
        )

    with st.spinner("Dosyalar yükleniyor..."):
        uploader.upload_files(
            folder_path="generated_files",
            bucket_name=bucket_name,
            endpoint_url=os.getenv("MINIO_ENDPOINT"),
            access_key=os.getenv("MINIO_ACCESS_KEY"),
            secret_key=os.getenv("MINIO_SECRET_KEY"),
            concurrency=ayarlar["concurrency"]
        )

    with st.spinner("Dosyalar indiriliyor..."):
        downloader.download_files(
            bucket_name=bucket_name,
            endpoint_url=os.getenv("MINIO_ENDPOINT"),
            access_key=os.getenv("MINIO_ACCESS_KEY"),
            secret_key=os.getenv("MINIO_SECRET_KEY"),
            indirilecek_klasor="downloaded_files",
            concurrency=ayarlar["concurrency"]
        )

    st.success("Benchmark tamamlandı!")

    sonuclar = metrics.tum_sonuclari_al()
    df = reporter.tabloya_cevir(sonuclar)
    ozet = reporter.ozet_cikar(df)

    st.subheader("Özet")
    st.write(f"Toplam dosya: {ozet['toplam_dosya']}")
    st.write(f"Başarılı: {ozet['basarili']} | Hatalı: {ozet['hatali']}")
    st.write(f"Ortalama süre: {ozet['ortalama_sure']:.4f} sn")
    st.write(f"En hızlı: {ozet['en_hizli']:.4f} sn | En yavaş: {ozet['en_yavas']:.4f} sn")

    st.subheader("Detaylı Sonuçlar")
    st.dataframe(df)