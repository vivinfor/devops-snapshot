import logging
import pandas as pd

from app.config import DONE_STATES, REWORK_TYPES, REWORK_STATES, EXCLUDE_TYPES

logger = logging.getLogger(__name__)


def generate_report(input_path: str, output_path: str) -> dict:
    """
    Lê o CSV extraído e gera relatório de backlog e retrabalho.
    Exclui artefatos de teste da análise de backlog.
    Retorna um dicionário com o resumo do relatório.
    """
    df = pd.read_csv(input_path)
    logger.info("Loaded %d work items from %s", len(df), input_path)

    # Remove artefatos de teste da análise (Test Plan, Test Suite, Test Case)
    excluded = df[df["type"].str.lower().isin(EXCLUDE_TYPES)]
    df_work = df[~df["type"].str.lower().isin(EXCLUDE_TYPES)]
    logger.info("Excluded %d test artifacts. Analyzing %d work items.", len(excluded), len(df_work))

    # Backlog: itens não concluídos
    backlog = df_work[~df_work["state"].str.lower().isin(DONE_STATES)]

    # Retrabalho: por tipo (Bug, etc.) ou por estado (Reopened)
    is_rework_type = df_work["type"].str.lower().isin(REWORK_TYPES)
    is_rework_state = df_work["state"].str.lower().isin(REWORK_STATES)
    rework = df_work[is_rework_type | is_rework_state]

    total = len(df_work)
    summary = {
        "total": total,
        "excluded": len(excluded),
        "backlog": len(backlog),
        "done": total - len(backlog),
        "rework": len(rework),
        "rework_pct": round(len(rework) / total * 100, 1) if total > 0 else 0,
    }

    # Backlog por tipo
    backlog_by_type = backlog.groupby("type").size().reset_index(name="count")

    # Retrabalho por responsável
    rework_by_assignee = rework.groupby("assigned_to").size().reset_index(name="count")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Resumo\n")
        f.write(f"Total de work items (excluindo artefatos de teste): {summary['total']}\n")
        f.write(f"Artefatos de teste excluídos: {summary['excluded']}\n")
        f.write(f"Backlog (não concluídos): {summary['backlog']}\n")
        f.write(f"Concluídos: {summary['done']}\n")
        f.write(f"Retrabalho: {summary['rework']} ({summary['rework_pct']}%)\n\n")

        f.write("# Backlog por Tipo\n")
        f.write(backlog_by_type.to_string(index=False))
        f.write("\n\n")

        f.write("# Retrabalho por Responsável\n")
        f.write(rework_by_assignee.to_string(index=False))
        f.write("\n")

    logger.info("Report saved to %s", output_path)
    return summary
