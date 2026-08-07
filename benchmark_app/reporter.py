import pandas as pd
from rich.console import Console
from rich.table import Table


def tabloya_cevir(sonuclar):
    df = pd.DataFrame(sonuclar)
    return df




def ozet_cikar(df):
    toplam_dosya = len(df)
    basarili_sayisi = df["basarili"].sum()
    hatali_sayisi = toplam_dosya - basarili_sayisi
    ortalama_sure = df["sure"].mean()
    en_yavas = df["sure"].max()
    en_hizli = df["sure"].min()
    toplam_sure = df["sure"].sum()
    # Throughput hesaplamaları
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

def durum_degerlendir(ozet):
    p95 = ozet["p95"]
    if p95 < 1:
        latency_durum = "İyi"
    elif p95 < 3:
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
    if throughput > 10:
        throughput_durum = "İyi"
    elif throughput >= 2:
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

    for _, satir in df.iterrows():
        durum = "✅ Başarılı" if satir["basarili"] else "❌ Hatalı"
        table.add_row(satir["dosya_adi"], satir["islem_tipi"], f"{satir['sure']:.4f}", durum)

    console.print(table)

    console.print(f"\n[bold]Özet:[/bold]")
    console.print(f"Toplam dosya: {ozet['toplam_dosya']}")
    console.print(f"Başarılı: {ozet['basarili']} | Hatalı: {ozet['hatali']}")
    console.print(f"Ortalama süre: {ozet['ortalama_sure']:.4f} sn")
    console.print(f"En hızlı: {ozet['en_hizli']:.4f} sn | En yavaş: {ozet['en_yavas']:.4f} sn")
    console.print(f"Toplam süre: {ozet['toplam_sure']:.4f} sn")
    # Throughput display 
    if "toplam_throughput_mb_s" in ozet:
        console.print(f"Toplam Throughput: {ozet['toplam_throughput_mb_s']:.4f} MB/s")
        console.print(f"Upload Throughput: {ozet['upload_throughput_mb_s']:.4f} MB/s | Download Throughput: {ozet['download_throughput_mb_s']:.4f} MB/s")