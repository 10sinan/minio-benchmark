import typer
import yaml

app = typer.Typer(add_completion=False)

@app.command()
def run(config: str = "config.yaml"):
    """Config dosyasını okuyup benchmark testini başlatır."""
    with open(config, "r") as f:
        settings = yaml.safe_load(f)

    typer.echo("Ayarlar yüklendi:")
    for key, value in settings.items():
        typer.echo(f"  {key}: {value}")

@app.command()
def placeholder():
    """Şimdilik boş - typer'ın tek-komut kısayol modunu devre dışı bırakmak için."""
    pass

if __name__ == "__main__":
    app()