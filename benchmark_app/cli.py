import os
import typer
import yaml
from dotenv import load_dotenv

import generator
import uploader
import downloader
import metrics
import reporter

load_dotenv()
app = typer.Typer(add_completion=False)


@app.command()
def run(config: str = "config.yaml", profile: str = "website"):
    with open(config, "r") as f:
        settings = yaml.safe_load(f)

    secili_profil = settings["profiles"][profile]
    bucket_name = settings["bucket_name"]

    typer.echo(f"Profil: {profile}")
    typer.echo("Ayarlar yüklendi, benchmark başlıyor...\n")

    typer.echo("Dosyalar üretiliyor...")
    generator.generate_files(
        folder_path="generated_files",
        file_count=secili_profil["file_count"],
        file_size_min_mb=secili_profil["file_size_min_mb"],
        file_size_max_mb=secili_profil["file_size_max_mb"]
    )

    typer.echo("\nDosyalar yükleniyor...")
    uploader.upload_files(
        folder_path="generated_files",
        bucket_name=bucket_name,
        endpoint_url=os.getenv("MINIO_ENDPOINT"),
        access_key=os.getenv("MINIO_ACCESS_KEY"),
        secret_key=os.getenv("MINIO_SECRET_KEY"),
        concurrency=secili_profil["concurrency"]
    )

    typer.echo("\nDosyalar indiriliyor...")
    downloader.download_files(
        bucket_name=bucket_name,
        endpoint_url=os.getenv("MINIO_ENDPOINT"),
        access_key=os.getenv("MINIO_ACCESS_KEY"),
        secret_key=os.getenv("MINIO_SECRET_KEY"),
        indirilecek_klasor="downloaded_files",
        concurrency=secili_profil["concurrency"]
    )

    typer.echo("\nRapor hazırlanıyor...\n")
    sonuclar = metrics.tum_sonuclari_al()
    df = reporter.tabloya_cevir(sonuclar)
    ozet = reporter.ozet_cikar(df)
    reporter.terminalde_goster(df, ozet)


@app.command()
def list_bucket(config: str = "config.yaml"):
    with open(config, "r") as f:
        settings = yaml.safe_load(f)

    dosyalar = downloader.list_files(
        bucket_name=settings["bucket_name"],
        endpoint_url=os.getenv("MINIO_ENDPOINT"),
        access_key=os.getenv("MINIO_ACCESS_KEY"),
        secret_key=os.getenv("MINIO_SECRET_KEY")
    )

    typer.echo(f"Bucket '{settings['bucket_name']}' icinde {len(dosyalar)} dosya var:\n")
    for dosya in dosyalar:
        typer.echo(f"  {dosya['dosya_adi']} - {dosya['boyut_byte']} byte")


if __name__ == "__main__":
    app()