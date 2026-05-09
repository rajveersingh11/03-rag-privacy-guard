"""
AegisVault — Celery Worker
---------------------------
Handles async ingestion tasks so the FastAPI event loop
never blocks on heavy NER / DP embedding operations.

Start worker:
    celery -A src.aegisVault.worker worker --loglevel=info --concurrency=4

Send task from app:
    from src.aegisVault.worker import ingest_document_task
    ingest_document_task.delay(text, metadata, tenant_id, acl_roles)
"""

import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

celery_app = Celery(
    "aegisvault",
    broker=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_concurrency=4,
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def ingest_document_task(self, text: str, metadata: dict,
                          tenant_id: str = "default",
                          acl_roles: list = None):
    """
    Celery task: runs the full ingestion pipeline asynchronously.
    Retries up to 3 times on transient failures.
    """
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_community.vectorstores import Chroma
        from src.aegisVault.config.manager import get_config
        from src.aegisVault.guards.privacy_math import DPEmbedder
        from src.aegisVault.pipeline.ingestion_pipeline import IngestionPipeline

        cfg = get_config()

        base_embedder = HuggingFaceEmbeddings(model_name=cfg.retrieval.embedding_model)
        dp_embedder   = DPEmbedder(base_embedder, cfg.dp.epsilon, cfg.dp.sensitivity) \
                        if cfg.dp.enabled else base_embedder

        vectorstore = Chroma(
            collection_name=cfg.retrieval.chroma_collection,
            embedding_function=dp_embedder,
            persist_directory=cfg.retrieval.chroma_persist_dir,
        )

        pipeline = IngestionPipeline(config=cfg, vectorstore=vectorstore)
        result   = pipeline.ingest(
            text=text, metadata=metadata,
            tenant_id=tenant_id, acl_roles=acl_roles or ["employee"],
        )
        return {"status": result.status, "doc_id": result.doc_id,
                "chunks": result.chunks_stored}

    except Exception as exc:
        raise self.retry(exc=exc)
