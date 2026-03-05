import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def upload_to_gcs(local_path: str, bucket_name: str, blob_name: str) -> str:
    """Faz upload de um arquivo local para o GCS e retorna o URI gs://."""
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(local_path)

    uri = f"gs://{bucket_name}/{blob_name}"
    logger.info("Uploaded %s to %s", local_path, uri)
    return uri
