import logging
import os
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


@app.command()
def fetch():
    """Extrai work items do Azure DevOps e salva CSV local."""
    from app.extract import fetch_and_save

    if not all([config.ORGANIZATION, config.PROJECT, config.PAT]):
        console.print("[red]Error: AZURE_DEVOPS_ORG, AZURE_DEVOPS_PROJECT e AZURE_DEVOPS_PAT são obrigatórios.[/red]")
        raise typer.Exit(1)

    output_dir = _ensure_output_dir()
    today = datetime.now().strftime("%Y-%m-%d")
    output_path = output_dir / f"work_items_{today}.csv"

    console.print(f"Fetching work items from [bold]{config.ORGANIZATION}/{config.PROJECT}[/bold]...")
    count = fetch_and_save(str(output_path))
    console.print(f"[green]Done.[/green] {count} work items saved to [bold]{output_path}[/bold]")


@app.command()
def report():
    """Lê o CSV mais recente e gera relatório de backlog e retrabalho."""
    from app.transform import generate_report

    output_dir = _ensure_output_dir()
    csvs = sorted(output_dir.glob("work_items_*.csv"), reverse=True)

    if not csvs:
        console.print("[red]No data found. Run 'fetch' first.[/red]")
        raise typer.Exit(1)

    input_path = csvs[0]
    report_path = output_dir / "report.txt"

    from app.report_html import generate_html_report

    console.print(f"Generating report from [bold]{input_path.name}[/bold]...")
    summary = generate_report(str(input_path), str(report_path))

    html_path = output_dir / "report.html"
    generate_html_report(str(input_path), str(html_path), summary, config.PROJECT or "Azure DevOps")

    table = Table(title="Azure DevOps Snapshot")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_row("Total work items", str(summary["total"]))
    table.add_row("Excluded (test artifacts)", str(summary["excluded"]))
    table.add_row("Backlog (not done)", str(summary["backlog"]))
    table.add_row("Done", str(summary["done"]))
    table.add_row("Rework", str(summary["rework"]))
    table.add_row("Rework %", f"{summary['rework_pct']}%")

    console.print(table)
    console.print(f"[green]Reports saved to[/green] [bold]{output_dir}/[/bold]")
    console.print(f"  · report.txt")
    console.print(f"  · report.html [cyan](open in browser)[/cyan]")


if __name__ == "__main__":
    app()
