"""
AegisVault — FastAPI Application (app/main.py)
------------------------------------------------
Production entry point when running from the src package layout.
Wires together all components, registers routers, and manages
lifespan (DB init, vectorstore, LLM client, Neo4j).

Start:
    uvicorn aegisVault.app.main:app --reload --port 8000
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

# ── Shared app state ───────────────────────────────────────────────────
state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise all services on startup, clean up on shutdown."""
    from langchain_openai import OpenAIEmbeddings
    from langchain_community.vectorstores import Chroma
    from openai import OpenAI

    from aegisVault.config.manager import get_config
    from aegisVault.components.privacy_math import DPEmbedder
    from aegisVault.components.graph_boundary import GraphBoundary
    from aegisVault.pipeline.ingestion_pipeline import IngestionPipeline
    from aegisVault.pipeline.inference_pipeline import InferencePipeline
    from aegisVault.access.rbac import RBACPolicy
    from aegisVault.db.session import init_db

    cfg = get_config()
    init_db()

    # ── DP-wrapped embedder ─────────────────────────────────────────
    base_emb = OpenAIEmbeddings(model=cfg.retrieval.embedding_model)
    embedder = (
        DPEmbedder(base_emb, cfg.dp.epsilon, cfg.dp.sensitivity)
        if cfg.dp.enabled else base_emb
    )

    # ── ChromaDB ────────────────────────────────────────────────────
    vectorstore = Chroma(
        collection_name=cfg.retrieval.chroma_collection,
        embedding_function=embedder,
        persist_directory=cfg.retrieval.chroma_persist_dir,
    )

    # ── OpenAI client ───────────────────────────────────────────────
    llm_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    # ── Neo4j graph (optional) ──────────────────────────────────────
    graph = None
    try:
        graph = GraphBoundary(cfg.graph)
        graph.ensure_schema()
    except Exception as e:
        import logging
        logging.getLogger("aegisVault").warning(f"Neo4j unavailable: {e}")

    # ── Pipelines ───────────────────────────────────────────────────
    state["cfg"]              = cfg
    state["vectorstore"]      = vectorstore
    state["llm_client"]       = llm_client
    state["graph"]            = graph
    state["rbac"]             = RBACPolicy(on_violation="drop")
    state["ingestion_pipeline"] = IngestionPipeline(cfg, vectorstore, graph)
    state["inference_pipeline"] = InferencePipeline(cfg, vectorstore, llm_client)

    yield  # ── App runs ──────────────────────────────────────────────

    if graph:
        graph.close()


# ── App factory ────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title="AegisVault — RAG Privacy Guard",
        version="1.0.0",
        description="2026 Enterprise RAG Security — 6-Layer Privacy Guard",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # ── Register routers ────────────────────────────────────────────
    from aegisVault.app.routers.query  import router as query_router
    from aegisVault.app.routers.ingest import router as ingest_router

    app.include_router(query_router,  prefix="/query",  tags=["Query"])
    app.include_router(ingest_router, prefix="/ingest", tags=["Ingest"])

    @app.get("/health", tags=["System"])
    def health():
        from aegisVault.db.session import health_check
        return {
            "status":   "ok",
            "version":  "1.0.0",
            "db":       "ok" if health_check() else "unreachable",
            "neo4j":    "ok" if state.get("graph") else "unavailable",
        }

    return app


app = create_app()