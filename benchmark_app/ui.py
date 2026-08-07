import logging
import threading
import time
import uuid

import actions
import generator
import history
import reporter
import s3_utils
import streamlit as st
import yaml

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)


def benchmark_calistir(
    ayarlar, endpoint, access_key, secret_key, bucket_name, test_prefix, iptal_kontrol, output_dict
):
    """
    Arka planda çalışacak thread fonksiyonu.
    Streamlit session_state'e DOĞRUDAN ERİŞMEZ (Thread-safe yapı).
    """
    try:
        df, ozet, upload_df, download_df = actions.run_benchmark(
            ayarlar=ayarlar,
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            bucket_name=bucket_name,
            test_prefix=test_prefix,
            iptal_kontrol=iptal_kontrol,
        )
        output_dict["sonuc"] = (df, ozet, upload_df, download_df)
    except Exception as e:
        logging.exception("Benchmark çalışırken hata: %s", e)
        output_dict["hata"] = str(e)


def render():
    # Session State Başlatma
    if "iptal_event" not in st.session_state:
        st.session_state.iptal_event = threading.Event()
    if "test_calisiyor" not in st.session_state:
        st.session_state.test_calisiyor = False
    if "benchmark_sonuc" not in st.session_state:
        st.session_state.benchmark_sonuc = None
    if "benchmark_hata" not in st.session_state:
        st.session_state.benchmark_hata = None
    if "benchmark_thread" not in st.session_state:
        st.session_state.benchmark_thread = None
    if "thread_output" not in st.session_state:
        st.session_state.thread_output = {}

    st.set_page_config(page_title="Benchmark Aracı", layout="wide")
    st.title("Benchmark Aracı")

    try:
        with open("config.yaml", "r") as f:
            settings = yaml.safe_load(f)
    except Exception as e:
        st.error(f"config.yaml dosyası okunamadı: {e}")
        return

    kolon_baglanti, kolon_ayarlar, kolon_bucket = st.columns(3)

    with kolon_baglanti:
        st.subheader("Bağlantı Bilgileri")
        endpoint = st.text_input(
            "Endpoint URL", placeholder="Örnek: http://192.168.1.10:9000"
        )
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
            file_count = st.number_input(
                "Dosya sayısı", min_value=1, value=int(file_count), step=1
            )
            file_size_min_mb = st.number_input(
                "Min boyut (MB)", min_value=0.0, value=float(file_size_min_mb), step=0.1
            )
            file_size_max_mb = st.number_input(
                "Max boyut (MB)", min_value=0.0, value=float(file_size_max_mb), step=0.1
            )
            concurrency = st.number_input(
                "Concurrency", min_value=1, value=int(concurrency), step=1
            )

    with kolon_bucket:
        st.subheader("Bucket Test Klasörleri")
        if not (bucket_name and endpoint and access_key and secret_key):
            st.info("Bağlantı bilgilerini doldurun.")
        else:
            try:
                prefixes = s3_utils.list_prefixes(
                    bucket_name, endpoint, access_key, secret_key
                )
                if not prefixes:
                    st.write("Hiç test klasörü bulunamadı.")
                else:
                    for idx, p in enumerate(prefixes):
                        col_isim, col_buton = st.columns([3, 1])
                        col_isim.write(p)
                        if col_buton.button("Sil", key=f"del_{p}_{idx}"):
                            deleted = s3_utils.delete_prefix(
                                bucket_name, p, endpoint, access_key, secret_key
                            )
                            if deleted:
                                st.success(f"{p} silindi")
                                st.rerun()
                            else:
                                st.error(f"{p} silinemedi")
            except Exception as e:
                logging.exception("Prefix listeleme/silme hatası: %s", e)
                st.error(f"S3 İşlem Hatası: {e}")

    st.divider()

    # Buton Alanı
    buton_kolon1, buton_kolon2 = st.columns([1, 4])
    with buton_kolon1:
        start_button = st.button(
            "Başlat", type="primary", disabled=st.session_state.test_calisiyor
        )
    with buton_kolon2:
        if st.session_state.test_calisiyor:
            if st.button("Durdur"):
                st.session_state.iptal_event.set()
                st.warning(
                    "İptal isteği alındı, mevcut işlem tamamlanınca durdurulacak..."
                )

    # Benchmark Başlatma Mantığı
    if start_button:
        if not endpoint or not access_key or not secret_key or not bucket_name:
            st.error("Lütfen tüm bağlantı bilgilerini doldurun.")
        else:
            try:
                with st.spinner("MinIO bağlantısı kontrol ediliyor..."):
                    s3_utils.baglanti_kontrolu(
                        endpoint, access_key, secret_key, bucket_name
                    )
            except Exception as hata:
                st.error(f"MinIO bağlantısı doğrulanamadı: {hata}")
            else:
                st.session_state.test_calisiyor = True
                st.session_state.iptal_event.clear()
                st.session_state.benchmark_sonuc = None
                st.session_state.benchmark_hata = None
                st.session_state.thread_output = {}

                ayarlar = {
                    "file_count": int(file_count),
                    "file_size_min_mb": float(file_size_min_mb),
                    "file_size_max_mb": float(file_size_max_mb),
                    "concurrency": int(concurrency),
                }

                test_prefix = f"test_{uuid.uuid4().hex[:8]}"

                # Thread'e st.session_state nesnesini sokmadan doğrudan Event.is_set metodunu gönderiyoruz
                iptal_event_obj = st.session_state.iptal_event

                thread = threading.Thread(
                    target=benchmark_calistir,
                    args=(
                        ayarlar,
                        endpoint,
                        access_key,
                        secret_key,
                        bucket_name,
                        test_prefix,
                        iptal_event_obj.is_set,
                        st.session_state.thread_output,
                    ),
                )
                st.session_state.benchmark_thread = thread
                thread.start()
                st.rerun()

    # Test Devam Ediyorsa Bekleme / Durum Kontrol Alanı
    if st.session_state.test_calisiyor:
        thread = st.session_state.benchmark_thread
        if thread and thread.is_alive():
            st.info("Benchmark çalışıyor...")
            time.sleep(1)
            st.rerun()
        else:
            # Thread bitti, sonuçları ana döngüde st.session_state'e aktar
            st.session_state.test_calisiyor = False
            output = st.session_state.thread_output
            if "hata" in output:
                st.session_state.benchmark_hata = output["hata"]
            elif "sonuc" in output:
                st.session_state.benchmark_sonuc = output["sonuc"]
            st.rerun()

    # Test Bittiğinde / Hata Varsa Gösterilecek Alan
    if st.session_state.benchmark_hata:
        st.error(
            f"Benchmark sırasında bir hata oluştu: {st.session_state.benchmark_hata}"
        )

    elif st.session_state.benchmark_sonuc is not None:
        df, ozet, upload_df, download_df = st.session_state.benchmark_sonuc

        if st.session_state.iptal_event.is_set():
            st.warning("Benchmark iptal edildi, o ana kadarki sonuçlar gösteriliyor.")
        else:
            st.success("Benchmark tamamlandı!")

        # Geçmişe Kaydet
        history.kaydet(
            profil_adi=secilen_profil if not ozel_ayarlar_kullan else "özel",
            bucket_name=bucket_name,
            ozet=ozet,
        )

        thresholds = settings["profiles"][secilen_profil]["thresholds"]
        durum = reporter.durum_degerlendir(ozet, thresholds)
        sozel = reporter.sozel_ozet(ozet, durum)

        with st.container():
            st.subheader("Özet")

            metrik_1, metrik_2, metrik_3, metrik_4 = st.columns(4)
            metrik_1.metric("Toplam Dosya", ozet.get("toplam_dosya", 0))
            metrik_2.metric("Başarılı", ozet.get("basarili", 0))
            metrik_3.metric("Hatalı", ozet.get("hatali", 0))
            metrik_4.metric("Ortalama Süre", f"{ozet.get('ortalama_sure', 0):.3f} sn")

            metrik_5, metrik_6, metrik_7, metrik_8 = st.columns(4)
            metrik_5.metric("P95", f"{ozet.get('p95', 0):.3f} sn")
            metrik_6.metric("P99", f"{ozet.get('p99', 0):.3f} sn")
            metrik_7.metric(
                "Toplam Throughput",
                f"{ozet.get('toplam_throughput_mb_s', 0):.2f} MB/s",
            )
            metrik_8.metric("Başarı Oranı", f"%{durum.get('basari_orani', 0):.1f}")

            st.write(sozel)

            st.caption(
                f"Gecikme: {durum.get('latency_durum', 'N/A')} | "
                f"Başarı: {durum.get('basari_durum', 'N/A')} | "
                f"Throughput: {durum.get('throughput_durum', 'N/A')}"
            )

            with st.expander("Değerlendirme kriterleri nedir?"):
                st.markdown(f"""
                    Bu değerlendirme, **{secilen_profil}** profiline göre yapılmıştır:
                    - **Gecikme (P95):** < {thresholds["latency_iyi_sn"]} sn → İyi · {thresholds["latency_iyi_sn"]}-{thresholds["latency_orta_sn"]} sn → Orta · > {thresholds["latency_orta_sn"]} sn → Yavaş
                    - **Başarı oranı:** %100 → Mükemmel · %95-99.9 → İyi · < %95 → Dikkat gerekiyor
                    - **Throughput:** > {thresholds["throughput_iyi_mb_s"]} MB/s → İyi · {thresholds["throughput_orta_mb_s"]}-{thresholds["throughput_iyi_mb_s"]} MB/s → Orta · < {thresholds["throughput_orta_mb_s"]} MB/s → Yavaş
                    """)

            upload_kolon, download_kolon = st.columns(2)
            with upload_kolon:
                st.subheader("Upload Sonuçları")
                st.dataframe(upload_df)

            with download_kolon:
                st.subheader("Download Sonuçları")
                st.dataframe(download_df)

    # Geçmiş Testler Tablosu
    st.divider()
    st.subheader("Geçmiş Testler")
    gecmis_df = history.gecmisi_oku()
    if gecmis_df is not None:
        st.dataframe(gecmis_df, use_container_width=True)
    else:
        st.write("Henüz kaydedilmiş test yok.")


if __name__ == "__main__":
    render()