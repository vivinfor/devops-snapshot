import csv
import logging
import requests
from requests.auth import HTTPBasicAuth
from tenacity import retry, stop_after_attempt, wait_fixed

from app.config import ORGANIZATION, PROJECT, PAT

logger = logging.getLogger(__name__)

HEADERS = {"Content-Type": "application/json"}
AUTH = HTTPBasicAuth("", PAT)
BATCH_SIZE = 200
FIELDS = [
    "System.WorkItemType",
    "System.Title",
    "System.State",
    "System.CreatedDate",
    "System.ChangedDate",
    "System.AssignedTo",
    "System.Tags",
]


@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
def _fetch_work_item_ids() -> list[int]:
    """Busca todos os IDs de work items via WIQL."""
    url = f"https://dev.azure.com/{ORGANIZATION}/{PROJECT}/_apis/wit/wiql?api-version=6.0"
    response = requests.post(
        url,
        json={"query": "SELECT [System.Id] FROM workitems"},
        headers=HEADERS,
        auth=AUTH,
        timeout=10,
    )
    response.raise_for_status()
    return [item["id"] for item in response.json().get("workItems", [])]


@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
def _fetch_batch(ids: list[int]) -> list[dict]:
    """Busca detalhes de um lote de work items (máximo 200)."""
    url = f"https://dev.azure.com/{ORGANIZATION}/{PROJECT}/_apis/wit/workitemsbatch?api-version=6.0"
    response = requests.post(
        url,
        json={"ids": ids, "fields": FIELDS},
        headers=HEADERS,
        auth=AUTH,
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("value", [])


def fetch_and_save(output_path: str) -> int:
    """
    Extrai todos os work items do Azure DevOps em lotes e salva em CSV.
    Retorna a quantidade de itens salvos.
    """
    logger.info("Fetching work item IDs from Azure DevOps...")
    ids = _fetch_work_item_ids()
    if not ids:
        logger.warning("No work items found.")
        return 0

    logger.info("Found %d work items. Fetching in batches of %d...", len(ids), BATCH_SIZE)

    csv_fields = ["id", "type", "title", "state", "created_date", "changed_date", "assigned_to", "tags"]
    rows = []

    for i in range(0, len(ids), BATCH_SIZE):
        batch = ids[i:i + BATCH_SIZE]
        logger.info("Fetching batch %d-%d...", i + 1, i + len(batch))
        items = _fetch_batch(batch)
        for item in items:
            f = item.get("fields", {})
            rows.append({
                "id": item.get("id", ""),
                "type": f.get("System.WorkItemType", ""),
                "title": f.get("System.Title", ""),
                "state": f.get("System.State", ""),
                "created_date": f.get("System.CreatedDate", ""),
                "changed_date": f.get("System.ChangedDate", ""),
                "assigned_to": f.get("System.AssignedTo", {}).get("displayName", ""),
                "tags": f.get("System.Tags", ""),
            })

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        writer.writerows(rows)

    logger.info("Saved %d work items to %s", len(rows), output_path)
    return len(rows)
