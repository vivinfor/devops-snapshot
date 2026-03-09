import logging
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from app import config

app = typer.Typer(help="CLI para extrair métricas do Azure DevOps e gerar relatórios locais.")
console = Console()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def _ensure_output_dir() -> Path:
    """Garante que o diretório de saída existe."""
    output = Path(config.OUTPUT_DIR)
    output.mkdir(parents=True, exist_ok=True)
    return output


def _slug(project: str) -> str:
    """Converte nome do projeto em slug para uso em nomes de arquivo."""
    normalized = unicodedata.normalize("NFD", project)
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_str.lower()).strip("-")


@app.command()
def fetch():
    """Extrai work items de todos os projetos configurados e salva CSVs locais."""
    from app.extract import fetch_and_save

    if not all([config.ORGANIZATION, config.PROJECTS, config.PAT]):
        console.print("[red]Error: AZURE_DEVOPS_ORG, AZURE_DEVOPS_PROJECT e AZURE_DEVOPS_PAT são obrigatórios.[/red]")
        raise typer.Exit(1)

    output_dir = _ensure_output_dir()
    today = datetime.now().strftime("%Y-%m-%d")

    for project in config.PROJECTS:
        slug = _slug(project)
        output_path = output_dir / f"work_items_{slug}_{today}.csv"

        console.print(f"Fetching work items from [bold]{config.ORGANIZATION}/{project}[/bold]...")
        count = fetch_and_save(str(output_path), project)
        console.print(f"[green]Done.[/green] {count} work items saved to [bold]{output_path}[/bold]")

        if config.GCS_BUCKET:
            import pandas as pd
            from app.storage import upload_to_gcs

            parquet_path = output_dir / f"work_items_{slug}_{today}.parquet"
            pd.read_csv(str(output_path)).to_parquet(str(parquet_path), index=False)

            blob_name = f"{config.GCS_PREFIX}/{slug}/work_items_{today}.parquet"
            uri = upload_to_gcs(str(parquet_path), config.GCS_BUCKET, blob_name)
            parquet_path.unlink()
            console.print(f"  · [cyan]Parquet uploaded to[/cyan] [bold]{uri}[/bold]")


@app.command()
def report():
    """Lê os CSVs mais recentes e gera um único relatório HTML consolidado."""
    from app.transform import compute_summary
    from app.report_html import generate_html_report

    output_dir = _ensure_output_dir()

    if not config.PROJECTS:
        console.print("[red]Error: AZURE_DEVOPS_PROJECT não configurado.[/red]")
        raise typer.Exit(1)

    projects_data = []
    for project in config.PROJECTS:
        slug = _slug(project)
        csvs = sorted(output_dir.glob(f"work_items_{slug}_*.csv"), reverse=True)

        if not csvs:
            console.print(f"[yellow]No data for '{project}'. Run 'fetch' first.[/yellow]")
            continue

        input_path = csvs[0]
        summary = compute_summary(str(input_path))
        projects_data.append({"project": project, "input_path": str(input_path), "summary": summary})

        table = Table(title=f"Azure DevOps Snapshot — {project}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        table.add_row("Total work items", str(summary["total"]))
        table.add_row("Ignored", str(summary["excluded"]))
        table.add_row("Backlog (not done)", str(summary["backlog"]))
        table.add_row("Done", str(summary["done"]))
        table.add_row("Rework", str(summary["rework"]))
        table.add_row("Rework %", f"{summary['rework_pct']}%")
        console.print(table)

    if not projects_data:
        raise typer.Exit(1)

    html_path = output_dir / "report.html"
    console.print(f"Generating report for [bold]{len(projects_data)} project(s)[/bold]...")
    generate_html_report(projects_data, str(html_path))
    console.print(f"[green]Report saved to[/green] [bold]{html_path}[/bold] [cyan](open in browser)[/cyan]")

    if config.GCS_BUCKET:
        from app.storage import upload_to_gcs

        blob_name = f"{config.GCS_PREFIX}/report.html"
        uri = upload_to_gcs(str(html_path), config.GCS_BUCKET, blob_name)
        console.print(f"  · [cyan]HTML uploaded to[/cyan] [bold]{uri}[/bold]")


if __name__ == "__main__":
    app()
