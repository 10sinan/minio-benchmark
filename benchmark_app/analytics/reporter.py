"""
reporter.py — Metrik analizi ve özet raporlama.

Yeni işlem tipleri: 'multipart_upload', 'list_objects', 'head_object', 'delete'
"""
import pandas as pd
from rich.console import Console
from rich.table import Table

# İşlem tipleri (UI'da gösterilecek sırada)
THROUGHPUT_TIPLER = ["upload", "download", "multipart_upload", "karma_upload", "karma_download"]
OPS_TIPLER = ["list_objects", "head_object", "delete", "karma_head"]


def tabloya_cevir(sonuclar):
    df = pd.DataFrame(sonuclar)
    return df


def sozel_ozet(ozet, durum):
    cumleler = []

    if durum.get("basari_durum") == "Dikkat gerekiyor":
        cumleler.append(
            f"⚠️ Dikkat: dosyaların %{100 - durum.get('basari_orani', 0):.1f}'i başarısız oldu, "
            f"bu bağlantı kararlılığı veya sunucu tarafında bir sorun olabileceğini gösteriyor."
        )
    elif durum.get("basari_durum") == "Mükemmel":
        cumleler.append("Tüm dosyalar başarıyla işlendi, sistem güvenilir çalışıyor.")
    else:
        cumleler.append(
            f"Dosyaların %{durum.get('basari_orani', 0):.1f}'i başarılı oldu, küçük bir hata oranı var."
        )

    if durum.get("latency_durum") == "İyi":
        cumleler.append("Gecikme süreleri düşük, sistem hızlı yanıt veriyor.")
    elif durum.get("latency_durum") == "Orta":
        cumleler.append("Gecikme süreleri kabul edilebilir seviyede, ama iyileştirmeye açık.")
    else:
        cumleler.append("Gecikme süreleri yüksek, kullanıcı deneyimini olumsuz etkileyebilir.")

    if durum.get("throughput_durum") == "İyi":
        cumleler.append("Veri aktarım hızı (throughput) yüksek.")
    elif durum.get("throughput_durum") == "Orta":
        cumleler.append("Veri aktarım hızı orta seviyede.")
    else:
        cumleler.append("Veri aktarım hızı düşük, ağ veya sunucu kapasitesi darboğaz olabilir.")

    upload_th = ozet.get("upload_throughput_mb_s")
    download_th = ozet.get("download_throughput_mb_s")
    if upload_th is not None and download_th is not None:
        if upload_th > download_th * 1.3:
            cumleler.append("Yükleme, indirmeden belirgin şekilde daha hızlı.")
        elif download_th > upload_th * 1.3:
            cumleler.append("İndirme, yüklemeden belirgin şekilde daha hızlı.")

    mp_th = ozet.get("multipart_upload_throughput_mb_s")
    up_th = ozet.get("upload_throughput_mb_s")
    if mp_th and up_th:
        if mp_th > up_th * 1.15:
            cumleler.append(
                f"Multipart Upload ({mp_th:.1f} MB/s), standart PutObject'ten "
                f"yaklaşık %{((mp_th / up_th) - 1) * 100:.0f} daha hızlı."
            )
        elif up_th > mp_th * 1.15:
            cumleler.append(
                f"Standart PutObject ({up_th:.1f} MB/s), Multipart Upload'dan "
                f"yaklaşık %{((up_th / mp_th) - 1) * 100:.0f} daha hızlı."
            )
        else:
            cumleler.append("Multipart Upload ve standart PutObject hızları birbirine yakın.")

    return " ".join(cumleler)


def _calc_mb_per_s(bytes_: int, seconds: float) -> float:
    if seconds and seconds > 0:
        return (bytes_ / (1024 * 1024)) / seconds
    return 0.0


def _throughput_for_type(df, islem_tipi: str) -> float:
    """Verilen işlem tipi için toplam throughput (MB/s) hesaplar."""
    inc = df[(df["islem_tipi"] == islem_tipi) & df["boyut_byte"].notna()]
    if inc.empty:
        return 0.0
    return _calc_mb_per_s(int(inc["boyut_byte"].sum()), float(inc["sure"].sum()))


def _ops_per_sec_for_type(df, islem_tipi: str) -> float:
    """Verilen işlem tipi için ops/sn hesaplar (metadata ve delete için)."""
    sub = df[df["islem_tipi"] == islem_tipi]
    if sub.empty:
        return 0.0
    toplam_sure = float(sub["sure"].sum())
    return len(sub) / toplam_sure if toplam_sure > 0 else 0.0


def ozet_cikar(df):
    if df.empty:
        return {
            "toplam_dosya": 0,
            "basarili": 0,
            "hatali": 0,
            "ortalama_sure": 0.0,
            "en_yavas": 0.0,
            "en_hizli": 0.0,
            "toplam_sure": 0.0,
            "toplam_throughput_mb_s": 0.0,
            "upload_throughput_mb_s": 0.0,
            "download_throughput_mb_s": 0.0,
            "multipart_upload_throughput_mb_s": 0.0,
            "karma_upload_throughput_mb_s": 0.0,
            "karma_download_throughput_mb_s": 0.0,
            "list_objects_ops_per_sec": 0.0,
            "head_object_ops_per_sec": 0.0,
            "delete_ops_per_sec": 0.0,
            "karma_head_ops_per_sec": 0.0,
            "p95": 0.0,
            "p99": 0.0,
        }

    # Temel istatistikler (tüm işlem tipleri dahil)
    toplam_dosya = len(df)
    basarili_sayisi = int(df["basarili"].sum())
    hatali_sayisi = toplam_dosya - basarili_sayisi
    ortalama_sure = float(df["sure"].mean())
    en_yavas = float(df["sure"].max())
    en_hizli = float(df["sure"].min())
    toplam_sure = float(df["sure"].sum())

    p95 = float(df["sure"].quantile(0.95))
    p99 = float(df["sure"].quantile(0.99))

    # Throughput hesapları (yalnızca boyut_byte olan satırlar)
    included = df[df["boyut_byte"].notna()] if "boyut_byte" in df.columns else df.iloc[0:0]
    toplam_bayt = int(included["boyut_byte"].sum()) if not included.empty else 0
    toplam_zaman = float(included["sure"].sum()) if not included.empty else 0.0
    toplam_throughput_mb_s = _calc_mb_per_s(toplam_bayt, toplam_zaman)

    return {
        "toplam_dosya": toplam_dosya,
        "basarili": basarili_sayisi,
        "hatali": hatali_sayisi,
        "ortalama_sure": ortalama_sure,
        "en_yavas": en_yavas,
        "en_hizli": en_hizli,
        "toplam_sure": toplam_sure,
        "toplam_throughput_mb_s": toplam_throughput_mb_s,
        # Standart throughput (MB/s)
        "upload_throughput_mb_s": _throughput_for_type(df, "upload"),
        "download_throughput_mb_s": _throughput_for_type(df, "download"),
        "multipart_upload_throughput_mb_s": _throughput_for_type(df, "multipart_upload"),
        # Karma throughput (MB/s)
        "karma_upload_throughput_mb_s": _throughput_for_type(df, "karma_upload"),
        "karma_download_throughput_mb_s": _throughput_for_type(df, "karma_download"),
        # Metadata ops/sn
        "list_objects_ops_per_sec": _ops_per_sec_for_type(df, "list_objects"),
        "head_object_ops_per_sec": _ops_per_sec_for_type(df, "head_object"),
        "delete_ops_per_sec": _ops_per_sec_for_type(df, "delete"),
        "karma_head_ops_per_sec": _ops_per_sec_for_type(df, "karma_head"),
        "p95": p95,
        "p99": p99,
    }


def durum_degerlendir(ozet, thresholds):
    if ozet["toplam_dosya"] == 0:
        return {
            "latency_durum": "Bilinmiyor",
            "basari_durum": "Bilinmiyor",
            "throughput_durum": "Bilinmiyor",
            "basari_orani": 0.0,
        }

    p95 = ozet["p95"]
    if p95 < thresholds["latency_iyi_sn"]:
        latency_durum = "İyi"
    elif p95 < thresholds["latency_orta_sn"]:
        latency_durum = "Orta"
    else:
        latency_durum = "Yavaş"

    basari_orani = (ozet["basarili"] / ozet["toplam_dosya"]) * 100
    if basari_orani == 100:
        basari_durum = "Mükemmel"
    elif basari_orani >= 95:
        basari_durum = "İyi"
    else:
        basari_durum = "Dikkat gerekiyor"

    throughput = ozet.get("toplam_throughput_mb_s", 0)
    if throughput > thresholds["throughput_iyi_mb_s"]:
        throughput_durum = "İyi"
    elif throughput >= thresholds["throughput_orta_mb_s"]:
        throughput_durum = "Orta"
    else:
        throughput_durum = "Yavaş"

    return {
        "latency_durum": latency_durum,
        "basari_durum": basari_durum,
        "throughput_durum": throughput_durum,
        "basari_orani": basari_orani,
    }


def terminalde_goster(df, ozet):
    console = Console()

    table = Table(title="Benchmark Sonuçları")
    table.add_column("Dosya Adı")
    table.add_column("İşlem")
    table.add_column("Süre (sn)")
    table.add_column("Durum")

    if not df.empty:
        for _, satir in df.iterrows():
            durum = "✅ Başarılı" if satir["basarili"] else "❌ Hatalı"
            table.add_row(
                satir["dosya_adi"],
                satir["islem_tipi"],
                f"{satir['sure']:.4f}",
                durum,
            )

    console.print(table)
    console.print("\n[bold]Özet:[/bold]")
    console.print(f"Toplam dosya: {ozet.get('toplam_dosya', 0)}")
    console.print(f"Başarılı: {ozet.get('basarili', 0)} | Hatalı: {ozet.get('hatali', 0)}")
    console.print(f"Ortalama süre: {ozet.get('ortalama_sure', 0):.4f} sn")
    console.print(
        f"En hızlı: {ozet.get('en_hizli', 0):.4f} sn | "
        f"En yavaş: {ozet.get('en_yavas', 0):.4f} sn"
    )
    console.print(f"Toplam süre: {ozet.get('toplam_sure', 0):.4f} sn")

    if "toplam_throughput_mb_s" in ozet:
        console.print(f"Toplam Throughput: {ozet['toplam_throughput_mb_s']:.4f} MB/s")
        console.print(
            f"Upload: {ozet.get('upload_throughput_mb_s', 0):.4f} MB/s | "
            f"Download: {ozet.get('download_throughput_mb_s', 0):.4f} MB/s | "
            f"Multipart: {ozet.get('multipart_upload_throughput_mb_s', 0):.4f} MB/s"
        )
        console.print(
            f"List ops/sn: {ozet.get('list_objects_ops_per_sec', 0):.2f} | "
            f"Head ops/sn: {ozet.get('head_object_ops_per_sec', 0):.2f} | "
            f"Delete ops/sn: {ozet.get('delete_ops_per_sec', 0):.2f}"
        )


def darbogaz_analizi_yap(df, ozet, resource_data):
    """
    Sistem kaynaklarını ve test özetini inceleyerek olası darboğazları (bottleneck) tespit eder.
    Dönen liste şu formattadır: [{"seviye": "error|warning|info", "mesaj": "..."}]
    """
    rapor = []
    
    # 1. Hata Oranı Kontrolü
    basari_orani = ozet.get("basari_orani", 100)
    if basari_orani < 95.0:
        rapor.append({
            "seviye": "error",
            "mesaj": f"Yüksek Hata Oranı: İsteklerin %{100 - basari_orani:.1f}'si başarısız oldu. Sunucu aşırı yüklenmiş veya kimlik bilgileri hatalı olabilir."
        })
        
    # 2. CPU ve RAM Kontrolü
    if resource_data and len(resource_data) > 0:
        cpu_avg = sum(r.get("cpu", 0) for r in resource_data) / len(resource_data)
        ram_avg = sum(r.get("ram_percent", 0) for r in resource_data) / len(resource_data)
        
        if cpu_avg > 85.0:
            rapor.append({
                "seviye": "error",
                "mesaj": f"İstemci CPU Darboğazı: Ortalama CPU kullanımı %{cpu_avg:.1f}. İşlemci test yükünü kaldırmakta zorlanıyor."
            })
        elif cpu_avg > 70.0:
            rapor.append({
                "seviye": "warning",
                "mesaj": f"Yüksek İstemci CPU: Ortalama CPU kullanımı %{cpu_avg:.1f} seviyesinde."
            })
            
        if ram_avg > 85.0:
            rapor.append({
                "seviye": "error",
                "mesaj": f"İstemci RAM Darboğazı: Ortalama RAM kullanımı %{ram_avg:.1f}. İstemci makinesinde yeterli bellek yok."
            })
            
    # 3. Gecikme (Latency) Kontrolü
    p95 = ozet.get("p95", 0)
    if p95 > 2.0:
        rapor.append({
            "seviye": "warning",
            "mesaj": f"Yüksek Gecikme: P95 gecikmesi {p95:.2f} saniye. Ağ veya sunucu yanıt verme süresi çok yavaş."
        })
        
    # Her şey yolundaysa
    if not rapor:
        rapor.append({
            "seviye": "success",
            "mesaj": "Sistem Sağlıklı: Belirgin bir istemci (client) darboğazı veya yüksek hata oranına rastlanmadı."
        })
        
    return rapor