import logging

import pandas as pd

from app.config import DONE_STATES, REWORK_TYPES, REWORK_STATES, EXCLUDE_TYPES

logger = logging.getLogger(__name__)


def compute_summary(input_path: str) -> dict:
    """
    Lê o CSV extraído e retorna o resumo de backlog e retrabalho.
    Exclui os tipos configurados em EXCLUDE_TYPES da análise.
    """
    df = pd.read_csv(input_path)
    logger.info("Loaded %d work items from %s", len(df), input_path)

    excluded = df[df["type"].str.lower().isin(EXCLUDE_TYPES)]
    df_work = df[~df["type"].str.lower().isin(EXCLUDE_TYPES)]
    logger.info("Excluded %d items. Analyzing %d work items.", len(excluded), len(df_work))

    backlog = df_work[~df_work["state"].str.lower().isin(DONE_STATES)]

    is_rework_type = df_work["type"].str.lower().isin(REWORK_TYPES)
    is_rework_state = df_work["state"].str.lower().isin(REWORK_STATES)
    rework = df_work[is_rework_type | is_rework_state]

    total = len(df_work)
    return {
        "total": total,
        "excluded": len(excluded),
        "backlog": len(backlog),
        "done": total - len(backlog),
        "rework": len(rework),
        "rework_pct": round(len(rework) / total * 100, 1) if total > 0 else 0,
    }
