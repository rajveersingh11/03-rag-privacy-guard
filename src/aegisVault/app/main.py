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

# ── UI Serving ──────────────────────────────────────────────────
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise all services on startup, clean up on shutdown."""
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_community.vectorstores import Chroma
    from openai import OpenAI

    from aegisVault.config.manager import get_config
    from aegisVault.guards.privacy_math import DPEmbedder
    from aegisVault.guards.graph_boundary import GraphBoundary
    from aegisVault.pipeline.ingestion_pipeline import IngestionPipeline
    from aegisVault.pipeline.inference_pipeline import InferencePipeline
    from aegisVault.access.rbac import RBACPolicy
    from aegisVault.db.session import init_db

    cfg = get_config()
    init_db()

    # ── DP-wrapped embedder ─────────────────────────────────────────
    base_emb = HuggingFaceEmbeddings(model_name=cfg.retrieval.embedding_model)
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

    # ── LLM client ──────────────────────────────────────────────────
    if "gemini" in cfg.llm.model_id.lower():
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm_client = ChatGoogleGenerativeAI(
            model=cfg.llm.model_id,
            google_api_key=os.environ.get("GOOGLE_API_KEY"),
            temperature=cfg.llm.temperature,
            max_output_tokens=cfg.llm.max_tokens,
        )
    else:
        from openai import OpenAI
        llm_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    # ── Neo4j graph (optional) ──────────────────────────────────────
    graph = None
    try:
        graph = GraphBoundary(cfg.graph)
        graph.ensure_schema()
    except Exception as e:
        import logging
        logging.getLogger("aegisVault").warning(f"Neo4j unavailable: {e}")

    # ── Pipelines ───────────────────────────────────────────────────
    app.state.cfg              = cfg
    app.state.vectorstore      = vectorstore
    app.state.llm_client       = llm_client
    app.state.graph            = graph
    app.state.rbac             = RBACPolicy(on_violation="drop")
    app.state.ingestion_pipeline = IngestionPipeline(cfg, vectorstore, graph)
    app.state.inference_pipeline = InferencePipeline(cfg, vectorstore, llm_client, graph=graph)

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

    cors_origins = [
        origin.strip()
        for origin in os.environ.get(
            "CORS_ALLOWED_ORIGINS",
            "http://127.0.0.1:8000,http://localhost:8000",
        ).split(",")
        if origin.strip()
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # ── Register routers ────────────────────────────────────────────
    from aegisVault.app.routers.query  import router as query_router
    from aegisVault.app.routers.ingest import router as ingest_router

    app.include_router(query_router,  prefix="/query",  tags=["Query"])
    app.include_router(ingest_router, prefix="/ingest", tags=["Ingest"])

    # ── UI Serving ──────────────────────────────────────────────────
    @app.get("/", response_class=HTMLResponse, tags=["UI"])
    async def index(request: Request):
        return templates.TemplateResponse(request=request, name="index.html")

    @app.get("/health", tags=["System"])
    def health(request: Request):
        from aegisVault.db.session import health_check
        return {
            "status":   "ok",
            "version":  "1.0.0",
            "db":       "ok" if health_check() else "unreachable",
            "neo4j":    "ok" if getattr(request.app.state, "graph", None) else "unavailable",
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
