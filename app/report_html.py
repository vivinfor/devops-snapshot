import logging
from datetime import date

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
    return counts[counts["count"] > 0]


def _charts_faixas(df_pbi: pd.DataFrame, df_bugs: pd.DataFrame) -> str:
    """Dois donuts lado a lado: PBI em backlog e bugs abertos por faixa de dias."""
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "pie"}, {"type": "pie"}]],
        subplot_titles=["PBI em Backlog × Dias em Aberto", "Bugs Abertos × Dias em Aberto"],
    )

    def _add_pie(df_open: pd.DataFrame, col: int) -> None:
        counts = _counts_faixas(df_open)
        fig.add_trace(go.Pie(
            labels=counts["faixa"],
            values=counts["count"],
            hole=0.4,
            textinfo="label+percent",
            textposition="outside",
            hovertemplate="%{label}<br>%{value} itens (%{percent})<extra></extra>",
            sort=False,
            showlegend=False,
        ), row=1, col=col)

    if not df_pbi.empty:
        _add_pie(df_pbi, 1)
    if not df_bugs.empty:
        _add_pie(df_bugs, 2)

    fig.update_layout(
        height=440,
        margin=dict(l=40, r=40, t=60, b=20),
        paper_bgcolor="white",
    )
    return fig.to_html(full_html=False, include_plotlyjs="cdn")


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <title>Azure Snapshot — {project}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2rem; background: #f0f2f5; color: #333; }}
        h1 {{ margin-bottom: 0.25rem; }}
        .subtitle {{ color: #888; margin-bottom: 2rem; font-size: 0.9rem; }}
        .cards {{ display: flex; gap: 1rem; margin-bottom: 2rem; flex-wrap: wrap; }}
        .card {{ background: white; padding: 1.5rem 2rem; border-radius: 8px; min-width: 150px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
        .card .label {{ font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: 0.05em; }}
        .card .value {{ font-size: 2.2rem; font-weight: 700; margin-top: 0.25rem; }}
        .card .unit {{ font-size: 0.85rem; color: #aaa; margin-top: 0.1rem; }}
        .card.warn .value {{ color: #e74c3c; }}
        .card.ok .value {{ color: #27ae60; }}
        .charts {{ background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
    </style>
</head>
<body>
    <h1>Azure Snapshot — {project}</h1>
    <div class="subtitle">Gerado em {generated_at} &nbsp;·&nbsp; {total} work items analisados (excluindo {excluded} artefatos de teste)</div>
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
        <div class="card">
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
    <div class="charts">
        {charts}
    </div>
</body>
</html>"""


def generate_html_report(input_path: str, output_path: str, summary: dict, project: str) -> None:
    """
    Lê o CSV extraído e gera relatório HTML focado em PBIs e Bugs.
    Cards: lead time PBI, backlog PBI, concluídos PBI, taxa de retrabalho.
    Gráficos: PBI e Bugs por faixa de dias em aberto (donuts lado a lado).
    """
    df = pd.read_csv(input_path)
    df_work = df[~df["type"].str.lower().isin(EXCLUDE_TYPES)]

    pbi = df_work[df_work["type"].str.lower() == PBI_TYPE]
    pbi_backlog = pbi[~pbi["state"].str.lower().isin(DONE_STATES)]
    pbi_done = pbi[pbi["state"].str.lower().isin(DONE_STATES)]

    # Lead time médio de PBIs concluídos
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

    charts = _charts_faixas(pbi_backlog, bugs_open)

    html = _HTML_TEMPLATE.format(
        project=project,
        generated_at=date.today().strftime("%d/%m/%Y"),
        total=summary["total"],
        excluded=summary["excluded"],
        pbi_backlog=len(pbi_backlog),
        pbi_done=len(pbi_done),
        pbi_lead_time=pbi_lead_time,
        rework_pct=rework_pct,
        rework=len(bugs),
        pbi_total=pbi_total,
        charts=charts,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info("HTML report saved to %s", output_path)
