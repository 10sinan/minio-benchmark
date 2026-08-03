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

    return {
        "toplam_dosya": toplam_dosya,
        "basarili": basarili_sayisi,
        "hatali": hatali_sayisi,
        "ortalama_sure": ortalama_sure,
        "en_yavas": en_yavas,
        "en_hizli": en_hizli,
        "toplam_sure": toplam_sure
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