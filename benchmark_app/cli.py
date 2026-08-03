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
def run(config: str = "config.yaml"):
    with open(config, "r") as f:
        settings = yaml.safe_load(f)

    typer.echo("Ayarlar yüklendi, benchmark başlıyor...\n")

    typer.echo("Dosyalar üretiliyor...")
    generator.generate_files(
        folder_path="generated_files",
        file_count=settings["file_count"],
        file_size_min_mb=settings["file_size_min_mb"],
        file_size_max_mb=settings["file_size_max_mb"]
    )

    typer.echo("\nDosyalar yükleniyor...")
    uploader.upload_files(
        folder_path="generated_files",
        bucket_name=settings["bucket_name"],
        endpoint_url=os.getenv("MINIO_ENDPOINT"),
        access_key=os.getenv("MINIO_ACCESS_KEY"),
        secret_key=os.getenv("MINIO_SECRET_KEY"),
        concurrency=settings["concurrency"]
    )

    typer.echo("\nDosyalar indiriliyor...")
    downloader.download_files(
        bucket_name=settings["bucket_name"],
        endpoint_url=os.getenv("MINIO_ENDPOINT"),
        access_key=os.getenv("MINIO_ACCESS_KEY"),
        secret_key=os.getenv("MINIO_SECRET_KEY"),
        indirilecek_klasor="downloaded_files",
        concurrency=settings["concurrency"]
    )

    typer.echo("\nRapor hazırlanıyor...\n")
    sonuclar = metrics.tum_sonuclari_al()
    df = reporter.tabloya_cevir(sonuclar)
    ozet = reporter.ozet_cikar(df)
    reporter.terminalde_goster(df, ozet)


@app.command()
def placeholder():
    pass


if __name__ == "__main__":
    app()