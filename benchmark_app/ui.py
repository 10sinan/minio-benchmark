import streamlit as st
import yaml
import uuid
import logging

import generator
import s3_utils
import actions
import history


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def render():
    st.set_page_config(page_title="MinIO Benchmark Aracı", layout="wide")
    st.title("MinIO Benchmark Aracı")

    with open("config.yaml", "r") as f:
        settings = yaml.safe_load(f)

    kolon_baglanti, kolon_ayarlar, kolon_bucket = st.columns(3)

    with kolon_baglanti:
        st.subheader("Bağlantı Bilgileri")
        endpoint = st.text_input("Endpoint URL", placeholder="Örnek: http://192.168.1.10:9000")
        access_key = st.text_input("Access Key")
        secret_key = st.text_input("Secret Key", type="password")
        bucket_name = st.text_input("Bucket adı", value=settings.get("bucket_name", ""))

    with kolon_ayarlar:
        st.subheader("Test Ayarları")

        profil_isimleri = list(settings["profiles"].keys())
        secilen_profil = st.selectbox("Profil seç", profil_isimleri)

        ozel_ayarlar_kullan = st.checkbox("Özel ayarlar kullan")

        varsayilan = settings["profiles"][secilen_profil]
        file_count = varsayilan["file_count"]
        file_size_min_mb = varsayilan["file_size_min_mb"]
        file_size_max_mb = varsayilan["file_size_max_mb"]
        concurrency = varsayilan["concurrency"]

        if ozel_ayarlar_kullan:
            file_count = st.number_input("Dosya sayısı", min_value=1, value=int(file_count), step=1)
            file_size_min_mb = st.number_input("Min boyut (MB)", min_value=0.0, value=float(file_size_min_mb), step=0.1)
            file_size_max_mb = st.number_input("Max boyut (MB)", min_value=0.0, value=float(file_size_max_mb), step=0.1)
            concurrency = st.number_input("Concurrency", min_value=1, value=int(concurrency), step=1)

    with kolon_bucket:
        st.subheader("Bucket Test Klasörleri")

        if not (bucket_name and endpoint and access_key and secret_key):
            st.info("Bağlantı bilgilerini doldurun.")
        else:
            prefixes = s3_utils.list_prefixes(bucket_name, endpoint, access_key, secret_key)
            if not prefixes:
                st.write("Hiç test klasörü bulunamadı.")
            else:
                for idx, p in enumerate(prefixes):
                    col_isim, col_buton = st.columns([3, 1])
                    col_isim.write(p)
                    if col_buton.button("Sil", key=f"del_{p}_{idx}"):
                        try:
                            deleted = s3_utils.delete_prefix(bucket_name, p, endpoint, access_key, secret_key)
                            if deleted:
                                st.success(f"{p} silindi")
                            else:
                                st.error(f"{p} silinemedi")
                        except Exception as e:
                            logging.exception("Prefix silme islemi sirasinda hata: %s", e)
                            st.error(f"Silme hatası: {e}")

    st.divider()
    start_button = st.button("Başlat", type="primary")

    if start_button:
        if not endpoint or not access_key or not secret_key or not bucket_name:
            st.error("Lütfen tüm bağlantı bilgilerini doldurun.")
            return

        try:
            with st.spinner("MinIO bağlantısı kontrol ediliyor..."):
                s3_utils.baglanti_kontrolu(endpoint, access_key, secret_key, bucket_name)
        except Exception as hata:
            st.error(f"MinIO bağlantısı doğrulanamadı: {hata}")
            return

        ayarlar = {
            "file_count": int(file_count),
            "file_size_min_mb": float(file_size_min_mb),
            "file_size_max_mb": float(file_size_max_mb),
            "concurrency": int(concurrency),
        }

        with st.spinner("Dosyalar üretiliyor..."):
            generator.generate_files(
                folder_path="generated_files",
                file_count=ayarlar["file_count"],
                file_size_min_mb=ayarlar["file_size_min_mb"],
                file_size_max_mb=ayarlar["file_size_max_mb"]
            )

        test_prefix = f"test_{uuid.uuid4().hex[:8]}"

        with st.spinner("Benchmark çalışıyor..."):
            df, ozet, upload_df, download_df = actions.run_benchmark(
                ayarlar=ayarlar,
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                bucket_name=bucket_name,
                test_prefix=test_prefix,
            )

        st.success("Benchmark tamamlandı!")

        history.kaydet(
            profil_adi=secilen_profil if not ozel_ayarlar_kullan else "özel",
            bucket_name=bucket_name,
            ozet=ozet
        )

        sonuc_container = st.container()
        with sonuc_container:
            st.subheader("Özet")
            st.write(f"Toplam dosya: {ozet['toplam_dosya']}")
            st.write(f"Başarılı: {ozet['basarili']} | Hatalı: {ozet['hatali']}")
            st.write(f"Ortalama süre: {ozet['ortalama_sure']:.4f} sn")
            st.write(f"En hızlı: {ozet['en_hizli']:.4f} sn | En yavaş: {ozet['en_yavas']:.4f} sn")

            toplam_th = ozet.get("toplam_throughput_mb_s")
            upload_th = ozet.get("upload_throughput_mb_s")
            download_th = ozet.get("download_throughput_mb_s")
            if toplam_th is not None:
                st.write(f"Throughput — toplam: {toplam_th:.2f} MB/s, upload: {upload_th:.2f} MB/s, download: {download_th:.2f} MB/s")

            upload_kolon, download_kolon = st.columns(2)

            with upload_kolon:
                st.subheader("Upload Sonuçları")
                st.dataframe(upload_df)

            with download_kolon:
                st.subheader("Download Sonuçları")
                st.dataframe(download_df)
                
            st.divider()
            st.subheader("Geçmiş Testler")
            gecmis_df = history.gecmisi_oku()
            if gecmis_df is not None:
                st.dataframe(gecmis_df)
            else:
                st.write("Henüz kaydedilmiş test yok.")