import streamlit as st
import yaml
import boto3
from boto3.session import Config

import generator
import uploader
import downloader
import metrics
import reporter


st.set_page_config(page_title="MinIO Benchmark Aracı", layout="wide")
st.title("MinIO Benchmark Aracı")

with open("config.yaml", "r") as f:
    settings = yaml.safe_load(f)


def s3_client_olustur(endpoint_url, access_key, secret_key):
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required"
        )
    )


def baglanti_kontrolu(endpoint_url, access_key, secret_key, bucket_name):
    s3 = s3_client_olustur(endpoint_url, access_key, secret_key)
    s3.list_buckets()
    s3.head_bucket(Bucket=bucket_name)


if "test_aktif" not in st.session_state:
    st.session_state.test_aktif = True

if "gelismis_aktif" not in st.session_state:
    st.session_state.gelismis_aktif = False


def test_aktif_degisince():
    if st.session_state.test_aktif:
        st.session_state.gelismis_aktif = False
    elif not st.session_state.gelismis_aktif:
        st.session_state.test_aktif = True


def gelismis_aktif_degisince():
    if st.session_state.gelismis_aktif:
        st.session_state.test_aktif = False
    elif not st.session_state.test_aktif:
        st.session_state.gelismis_aktif = True


sol_kolon, orta_kolon, sag_kolon = st.columns([1, 1, 1])

with sol_kolon:
    st.subheader("MinIO Bağlantı Bilgileri")
    endpoint = st.text_input(
        "Endpoint URL",
        placeholder="Örnek: http://192.168.1.10:9000",
    )
    access_key = st.text_input("Access Key")
    secret_key = st.text_input("Secret Key", type="password")

with orta_kolon:
    orta_baslik, orta_kutu = st.columns([4, 1])
    with orta_baslik:
        st.subheader("Test Ayarları")
    with orta_kutu:
        st.checkbox("Aktif", key="test_aktif", on_change=test_aktif_degisince)

    profil_isimleri = list(settings["profiles"].keys())
    secilen_profil = st.selectbox("Profil seç", profil_isimleri, disabled=st.session_state.gelismis_aktif)
    bucket_name = st.text_input(
        "Bucket adı",
        value=settings.get("bucket_name", ""),
        disabled=st.session_state.gelismis_aktif,
    )
    st.caption(
        "Bu sütun aktifse profil seçimi ve bucket ayarı kullanılır."
    )

with sag_kolon:
    sag_baslik, sag_kutu = st.columns([4, 1])
    with sag_baslik:
        st.subheader("Gelişmiş Test Ayarları")
    with sag_kutu:
        st.checkbox("Aktif", key="gelismis_aktif", on_change=gelismis_aktif_degisince)

    ayarlar = settings["profiles"][secilen_profil]
    file_count = st.number_input(
        "Dosya sayısı",
        min_value=1,
        value=int(ayarlar["file_count"]),
        step=1,
        disabled=not st.session_state.gelismis_aktif,
    )
    file_size_min_mb = st.number_input(
        "Minimum dosya boyutu (MB)",
        min_value=0.0,
        value=float(ayarlar["file_size_min_mb"]),
        step=0.1,
        disabled=not st.session_state.gelismis_aktif,
    )
    file_size_max_mb = st.number_input(
        "Maksimum dosya boyutu (MB)",
        min_value=0.0,
        value=float(ayarlar["file_size_max_mb"]),
        step=0.1,
        disabled=not st.session_state.gelismis_aktif,
    )
    concurrency = st.number_input(
        "Concurrency",
        min_value=1,
        value=int(ayarlar["concurrency"]),
        step=1,
        disabled=not st.session_state.gelismis_aktif,
    )


start_button = st.button("Başlat", use_container_width=True)

if start_button:
    if not endpoint or not access_key or not secret_key:
        st.error("Lütfen tüm bağlantı bilgilerini doldurun.")
    elif not st.session_state.test_aktif and not st.session_state.gelismis_aktif:
        st.error("Devam etmek için test ayarlarından birini aktif etmelisin.")
    else:
        try:
            with st.spinner("MinIO bağlantısı kontrol ediliyor..."):
                baglanti_kontrolu(endpoint, access_key, secret_key, bucket_name)
        except Exception as hata:
            st.error(f"MinIO bağlantısı doğrulanamadı: {hata}")
        else:
            if st.session_state.gelismis_aktif:
                ayarlar = {
                    "file_count": int(file_count),
                    "file_size_min_mb": float(file_size_min_mb),
                    "file_size_max_mb": float(file_size_max_mb),
                    "concurrency": int(concurrency),
                }
            else:
                ayarlar = settings["profiles"][secilen_profil]

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
                    endpoint_url=endpoint,
                    access_key=access_key,
                    secret_key=secret_key,
                    concurrency=ayarlar["concurrency"]
                )

            with st.spinner("Dosyalar indiriliyor..."):
                downloader.download_files(
                    bucket_name=bucket_name,
                    endpoint_url=endpoint,
                    access_key=access_key,
                    secret_key=secret_key,
                    indirilecek_klasor="downloaded_files",
                    concurrency=ayarlar["concurrency"]
                )

            st.success("Benchmark tamamlandı!")

            sonuclar = metrics.tum_sonuclari_al()
            df = reporter.tabloya_cevir(sonuclar)
            ozet = reporter.ozet_cikar(df)
            upload_df = df[df["islem_tipi"] == "upload"].copy()
            download_df = df[df["islem_tipi"] == "download"].copy()

            if "boyut_byte" in upload_df.columns:
                upload_df["boyut_mb"] = upload_df["boyut_byte"] / (1024 * 1024)
                upload_df = upload_df.drop(columns=["boyut_byte"])

            if "boyut_byte" in download_df.columns:
                download_df["boyut_mb"] = download_df["boyut_byte"] / (1024 * 1024)
                download_df = download_df.drop(columns=["boyut_byte"])

            ozeti_kolon, detay_kolon = st.columns([1, 2])

            with ozeti_kolon:
                st.subheader("Özet")
                st.metric("Toplam dosya", ozet["toplam_dosya"])
                st.metric("Başarılı", ozet["basarili"])
                st.metric("Hatalı", ozet["hatali"])
                st.write(f"Ortalama süre: {ozet['ortalama_sure']:.4f} sn")
                st.write(f"En hızlı: {ozet['en_hizli']:.4f} sn")
                st.write(f"En yavaş: {ozet['en_yavas']:.4f} sn")

            with detay_kolon:
                st.subheader("Detaylı Sonuçlar")
                upload_kolon, download_kolon = st.columns(2)

                with upload_kolon:
                    st.caption("Upload sonuçları")
                    st.dataframe(upload_df, use_container_width=True)

                with download_kolon:
                    st.caption("Download sonuçları")
                    st.dataframe(download_df, use_container_width=True)