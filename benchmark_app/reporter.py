import pandas as pd
from rich.console import Console
from rich.table import Table


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
        cumleler.append(f"Dosyaların %{durum.get('basari_orani', 0):.1f}'i başarılı oldu, küçük bir hata oranı var.")

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

    return " ".join(cumleler)


def ozet_cikar(df):
    if df.empty:
        return {
            "toplam_dosya": 0, "basarili": 0, "hatali": 0,
            "ortalama_sure": 0.0, "en_yavas": 0.0, "en_hizli": 0.0,
            "toplam_sure": 0.0, "toplam_throughput_mb_s": 0.0,
            "upload_throughput_mb_s": 0.0, "download_throughput_mb_s": 0.0,
            "p95": 0.0, "p99": 0.0,
        }
        
    toplam_dosya = len(df)
    basarili_sayisi = df["basarili"].sum()
    hatali_sayisi = toplam_dosya - basarili_sayisi
    ortalama_sure = df["sure"].mean()
    en_yavas = df["sure"].max()
    en_hizli = df["sure"].min()
    toplam_sure = df["sure"].sum()
    
    included = df[df["boyut_byte"].notna()] if "boyut_byte" in df.columns else df.iloc[0:0]
    toplam_bayt = int(included["boyut_byte"].sum()) if not included.empty else 0
    toplam_zaman = float(included["sure"].sum()) if not included.empty else 0.0

    def _calc_mb_per_s(bytes_, seconds):
        if seconds and seconds > 0:
            return (bytes_ / (1024 * 1024)) / seconds
        return 0.0

    toplam_throughput_mb_s = _calc_mb_per_s(toplam_bayt, toplam_zaman)

    upload_inc = included[included["islem_tipi"] == "upload"] if not included.empty else included
    download_inc = included[included["islem_tipi"] == "download"] if not included.empty else included

    upload_bayt = int(upload_inc["boyut_byte"].sum()) if not upload_inc.empty else 0
    upload_zaman = float(upload_inc["sure"].sum()) if not upload_inc.empty else 0.0
    upload_throughput_mb_s = _calc_mb_per_s(upload_bayt, upload_zaman)

    download_bayt = int(download_inc["boyut_byte"].sum()) if not download_inc.empty else 0
    download_zaman = float(download_inc["sure"].sum()) if not download_inc.empty else 0.0
    download_throughput_mb_s = _calc_mb_per_s(download_bayt, download_zaman)

    p95 = df["sure"].quantile(0.95)
    p99 = df["sure"].quantile(0.99)

    return {
        "toplam_dosya": toplam_dosya,
        "basarili": basarili_sayisi,
        "hatali": hatali_sayisi,
        "ortalama_sure": ortalama_sure,
        "en_yavas": en_yavas,
        "en_hizli": en_hizli,
        "toplam_sure": toplam_sure,
        "toplam_throughput_mb_s": toplam_throughput_mb_s,
        "upload_throughput_mb_s": upload_throughput_mb_s,
        "download_throughput_mb_s": download_throughput_mb_s,
        "p95": p95,
        "p99": p99,
    }


def durum_degerlendir(ozet, thresholds):
    if ozet["toplam_dosya"] == 0:
        return {
            "latency_durum": "Bilinmiyor",
            "basari_durum": "Bilinmiyor",
            "throughput_durum": "Bilinmiyor",
            "basari_orani": 0.0
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
        "basari_orani": basari_orani
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
            table.add_row(satir["dosya_adi"], satir["islem_tipi"], f"{satir['sure']:.4f}", durum)

    console.print(table)

    console.print(f"\n[bold]Özet:[/bold]")
    console.print(f"Toplam dosya: {ozet.get('toplam_dosya', 0)}")
    console.print(f"Başarılı: {ozet.get('basarili', 0)} | Hatalı: {ozet.get('hatali', 0)}")
    console.print(f"Ortalama süre: {ozet.get('ortalama_sure', 0):.4f} sn")
    console.print(f"En hızlı: {ozet.get('en_hizli', 0):.4f} sn | En yavaş: {ozet.get('en_yavas', 0):.4f} sn")
    console.print(f"Toplam süre: {ozet.get('toplam_sure', 0):.4f} sn")
    
    if "toplam_throughput_mb_s" in ozet:
        console.print(f"Toplam Throughput: {ozet['toplam_throughput_mb_s']:.4f} MB/s")
        console.print(f"Upload Throughput: {ozet.get('upload_throughput_mb_s', 0):.4f} MB/s | Download Throughput: {ozet.get('download_throughput_mb_s', 0):.4f} MB/s")