import logging
from datetime import date

import pandas as pd

from app.config import DONE_STATES, EXCLUDE_TYPES

logger = logging.getLogger(__name__)

PBI_TYPE = "product backlog item"
BUG_TYPE = "bug"

FAIXAS_LABELS = ["0-10 dias", "11-25 dias", "26-35 dias", "> 35 dias"]


def _faixa(days: int) -> str:
    """Classifica o número de dias em aberto em uma faixa."""
    if days <= 10:
        return "0-10 dias"
    elif days <= 25:
        return "11-25 dias"
    elif days <= 35:
        return "26-35 dias"
    return "> 35 dias"


def _days_open(df: pd.DataFrame) -> pd.Series:
    """Calcula os dias em aberto a partir de created_date até hoje."""
    today = pd.Timestamp.now(tz="UTC")
    created = pd.to_datetime(df["created_date"], utc=True)
    return (today - created).dt.days


def _counts_faixas(df_open: pd.DataFrame) -> pd.DataFrame:
    """Retorna contagem por faixa de dias em aberto."""
    df_open = df_open.copy()
    df_open["days_open"] = _days_open(df_open)
    df_open["faixa"] = df_open["days_open"].apply(_faixa)
    counts = (
        df_open["faixa"]
        .value_counts()
        .reindex(FAIXAS_LABELS, fill_value=0)
        .reset_index()
    )
    counts.columns = ["faixa", "count"]
    return counts


def _table_faixas(df_open: pd.DataFrame, title: str) -> str:
    """Tabela estilizada de itens em aberto por faixa de dias."""
    counts = _counts_faixas(df_open)
    total = counts["count"].sum()

    rows = ""
    for _, row in counts.iterrows():
        pct = round(row["count"] / total * 100, 1) if total > 0 else 0
        rows += (
            f"<tr>"
            f"<td>{row['faixa']}</td>"
            f"<td class='num'>{row['count']}</td>"
            f"<td class='num'>{pct}%</td>"
            f"</tr>"
        )

    total_row = f"<tr class='total'><td>Total</td><td class='num'>{total}</td><td class='num'>100%</td></tr>"

    return (
        f"<div class='data-table'>"
        f"<div class='table-title'>{title}</div>"
        f"<table>"
        f"<thead><tr><th>Faixa</th><th class='num'>Itens</th><th class='num'>%</th></tr></thead>"
        f"<tbody>{rows}{total_row}</tbody>"
        f"</table>"
        f"</div>"
    )


def _table_pbi_por_projeto(projects_pbi: list[tuple[str, int]]) -> str:
    """Tabela estilizada de PBI em aberto por projeto."""
    total = sum(v for _, v in projects_pbi)

    rows = ""
    for name, count in projects_pbi:
        pct = round(count / total * 100, 1) if total > 0 else 0
        rows += (
            f"<tr>"
            f"<td>{name}</td>"
            f"<td class='num'>{count}</td>"
            f"<td class='num'>{pct}%</td>"
            f"</tr>"
        )

    total_row = f"<tr class='total'><td>Total</td><td class='num'>{total}</td><td class='num'>100%</td></tr>"

    return (
        f"<div class='data-table'>"
        f"<div class='table-title'>PBI em Aberto por Projeto</div>"
        f"<table>"
        f"<thead><tr><th>Projeto</th><th class='num'>PBI em Aberto</th><th class='num'>%</th></tr></thead>"
        f"<tbody>{rows}{total_row}</tbody>"
        f"</table>"
        f"</div>"
    )


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <title>Azure Snapshot</title>
    <style>
        :root {{
            --navy:  #133467;
            --blue:  #0137F0;
            --purple:#7A4D80;
            --orange:#FF6506;
            --teal:  #7AF1DE;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            margin: 0; background: #f4f6fb; color: #1a1a2e;
        }}
        header {{
            background: var(--navy);
            color: white;
            padding: 1.75rem 2.5rem 1.5rem;
            border-bottom: 4px solid var(--teal);
        }}
        header h1 {{ margin: 0 0 0.3rem; font-size: 1.6rem; font-weight: 700; letter-spacing: -0.01em; }}
        header .subtitle {{ color: rgba(255,255,255,0.55); font-size: 0.85rem; }}
        main {{ padding: 2rem 2.5rem; }}
        .cards {{ display: flex; gap: 1rem; margin-bottom: 2rem; flex-wrap: wrap; }}
        .card {{
            background: white;
            padding: 1.25rem 1.75rem;
            border-radius: 10px;
            min-width: 160px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.07);
            border-top: 3px solid var(--blue);
        }}
        .card.ok   {{ border-top-color: var(--teal); }}
        .card.lead {{ border-top-color: var(--purple); }}
        .card.warn {{ border-top-color: var(--orange); }}
        .card .label {{
            font-size: 0.72rem; color: #888;
            text-transform: uppercase; letter-spacing: 0.06em; font-weight: 600;
        }}
        .card .value {{
            font-size: 2.4rem; font-weight: 800; margin-top: 0.2rem;
            color: var(--navy);
        }}
        .card.ok   .value {{ color: #0a9e82; }}
        .card.warn .value {{ color: var(--orange); }}
        .card .unit {{ font-size: 0.8rem; color: #aaa; margin-top: 0.15rem; }}
        .tables-row {{ display: flex; flex-direction: column; gap: 1rem; }}
        .data-table {{
            background: white;
            border-radius: 10px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.07);
            width: 400px;
            overflow: hidden;
        }}
        .table-title {{
            font-weight: 700; font-size: 0.85rem;
            padding: 0.85rem 1.25rem;
            background: var(--navy); color: white;
            letter-spacing: 0.02em;
        }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
        thead th {{
            text-align: left; color: #888; font-weight: 600;
            font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em;
            padding: 0.6rem 1.25rem; background: #f9f9fb;
            border-bottom: 1px solid #eee;
        }}
        tbody td {{ padding: 0.5rem 1.25rem; border-bottom: 1px solid #f2f2f5; color: #333; }}
        tbody tr:last-child td {{ border-bottom: none; }}
        tbody tr:hover td {{ background: #fafbff; }}
        .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
        tr.total td {{
            font-weight: 700; color: var(--navy);
            border-top: 2px solid #e8eaf0; border-bottom: none;
            background: #f4f6fb;
        }}
    </style>
</head>
<body>
    <header>
        <h1>Azure Snapshot</h1>
        <div class="subtitle">Gerado em {generated_at} &nbsp;·&nbsp; {total} work items analisados{excluded_note}</div>
    </header>
    <main>
        <div class="cards">
            <div class="card">
                <div class="label">PBI em Backlog</div>
                <div class="value">{pbi_backlog}</div>
                <div class="unit">Product Backlog Items</div>
            </div>
            <div class="card ok">
                <div class="label">PBI Concluídos</div>
                <div class="value">{pbi_done}</div>
                <div class="unit">Product Backlog Items</div>
            </div>
            <div class="card lead">
                <div class="label">Lead Time Médio PBI</div>
                <div class="value">{pbi_lead_time}</div>
                <div class="unit">dias até conclusão</div>
            </div>
            <div class="card warn">
                <div class="label">Taxa de Retrabalho</div>
                <div class="value">{rework_pct}%</div>
                <div class="unit">{rework} bugs / {pbi_total} PBIs</div>
            </div>
        </div>
        <div class="tables-row">
            {table_pbi}
            {table_bugs}
            {table_multi}
        </div>
    </main>
</body>
</html>"""


def generate_html_report(projects_data: list[dict], output_path: str) -> None:
    """
    Gera relatório HTML unificado com dados agregados de todos os projetos.
    Se houver mais de um projeto, adiciona tabela comparativa por projeto ao final.

    projects_data: lista de dicts com keys: project, input_path, summary
    """
    frames = []
    for item in projects_data:
        df = pd.read_csv(item["input_path"])
        frames.append(df)

    df_all = pd.concat(frames, ignore_index=True)
    df_work = df_all[~df_all["type"].str.lower().isin(EXCLUDE_TYPES)]

    type_counts = df_work["type"].value_counts().to_dict()
    logger.info("Work item types found: %s", type_counts)

    pbi = df_work[df_work["type"].str.lower() == PBI_TYPE]
    pbi_backlog = pbi[~pbi["state"].str.lower().isin(DONE_STATES)]
    pbi_done = pbi[pbi["state"].str.lower().isin(DONE_STATES)]

    if not pbi_done.empty:
        lt = pbi_done.copy()
        lt["created_date"] = pd.to_datetime(lt["created_date"], utc=True)
        lt["changed_date"] = pd.to_datetime(lt["changed_date"], utc=True)
        pbi_lead_time = round((lt["changed_date"] - lt["created_date"]).dt.days.mean(), 1)
    else:
        pbi_lead_time = "—"

    bugs = df_work[df_work["type"].str.lower() == BUG_TYPE]
    bugs_open = bugs[~bugs["state"].str.lower().isin(DONE_STATES)]

    pbi_total = len(pbi)
    rework_pct = round(len(bugs) / pbi_total * 100, 1) if pbi_total > 0 else 0

    total_excluded = sum(item["summary"]["excluded"] for item in projects_data)
    total_items = sum(item["summary"]["total"] for item in projects_data)
    excluded_note = f" &nbsp;·&nbsp; {total_excluded} itens ignorados" if total_excluded > 0 else ""

    table_pbi = _table_faixas(pbi_backlog, "PBI em Backlog × Dias em Aberto")
    table_bugs = _table_faixas(bugs_open, "Bugs Abertos × Dias em Aberto")

    table_multi = ""
    if len(projects_data) > 1:
        pbi_por_projeto = []
        for item in projects_data:
            df_p = pd.read_csv(item["input_path"])
            df_w = df_p[~df_p["type"].str.lower().isin(EXCLUDE_TYPES)]
            p = df_w[df_w["type"].str.lower() == PBI_TYPE]
            count = len(p[~p["state"].str.lower().isin(DONE_STATES)])
            pbi_por_projeto.append((item["project"], count))
        table_multi = _table_pbi_por_projeto(pbi_por_projeto)

    html = _HTML_TEMPLATE.format(
        generated_at=date.today().strftime("%d/%m/%Y"),
        total=total_items,
        excluded_note=excluded_note,
        pbi_backlog=len(pbi_backlog),
        pbi_done=len(pbi_done),
        pbi_lead_time=pbi_lead_time,
        rework_pct=rework_pct,
        rework=len(bugs),
        pbi_total=pbi_total,
        table_pbi=table_pbi,
        table_bugs=table_bugs,
        table_multi=table_multi,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info("HTML report saved to %s", output_path)
