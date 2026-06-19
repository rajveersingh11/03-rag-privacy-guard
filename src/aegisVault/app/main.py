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

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

load_dotenv()

from aegisVault.utils.common import setup_logging, trace_id_ctx, tenant_id_ctx, user_id_ctx
setup_logging()

# ── Shared app state ───────────────────────────────────────────────────
state: dict = {}

# ── UI Serving ──────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise all services on startup, clean up on shutdown."""
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma
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

    # ── Canary Tokens ───────────────────────────────────────────────
    import secrets
    from aegisVault.utils.common import get_logger
    
    if not cfg.output_sanitizer.canary_tokens or "change-me" in cfg.output_sanitizer.canary_tokens[0].lower():
        canary = f"AEGIS-CANARY-{secrets.token_hex(8).upper()}"
        cfg.output_sanitizer.canary_tokens = [canary]
        try:
            vectorstore.add_texts(
                texts=[f"This is a canary record. Reference ID: {canary}. Do not share."],
                metadatas=[{
                    "doc_id": "system_canary",
                    "sensitivity_class": "RESTRICTED",
                    "tenant_id": "system",
                    "acl_roles": '["admin"]'
                }]
            )
            get_logger("aegisVault.app").info(f"Generated and inserted new canary token: {canary}")
        except Exception as e:
            get_logger("aegisVault.app").error(f"Failed to insert canary token: {e}")

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
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from aegisVault.app.deps import limiter
import uuid
import contextvars

# Context var for tracing
trace_id_ctx = contextvars.ContextVar("trace_id", default="")

def create_app() -> FastAPI:
    is_prod = os.environ.get("APP_ENV") == "production"
    
    app = FastAPI(
        title="AegisVault — RAG Privacy Guard",
        version="1.0.0",
        description="2026 Enterprise RAG Security — 6-Layer Privacy Guard",
        lifespan=lifespan,
        docs_url=None if is_prod else "/docs",
        redoc_url=None if is_prod else "/redoc",
        openapi_tags=[
            {"name": "Query", "description": "Guarded real-time query interface"},
            {"name": "Ingest", "description": "Document ingestion with PII scrubbing and DP embedding"},
            {"name": "Events", "description": "Security events and compliance audit logs"},
            {"name": "Auth", "description": "Admin authentication and user provisioning"},
            {"name": "System", "description": "Health probes and metrics"},
            {"name": "UI", "description": "Web interface"},
        ]
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    cors_origins = [
        origin.strip()
        for origin in os.environ.get(
            "CORS_ALLOWED_ORIGINS",
            "http://127.0.0.1:8000,http://localhost:8000,http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]
    
    if os.environ.get("APP_ENV") == "production" and "*" in cors_origins:
        raise RuntimeError("Wildcard CORS (*) is not allowed in production.")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    is_prod = os.environ.get("APP_ENV") == "production"
    dist_dir = os.path.abspath(os.path.join(BASE_DIR, "../../../frontend/dist"))
    
    if is_prod and os.path.exists(dist_dir):
        assets_dir = os.path.join(dist_dir, "assets")
        if os.path.exists(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    else:
        app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.trace_id = req_id
        token = trace_id_ctx.set(req_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            trace_id_ctx.reset(token)

    @app.middleware("http")
    async def metrics_security_middleware(request: Request, call_next):
        if request.url.path == "/metrics":
            client_ip = request.client.host if request.client else ""
            metrics_token = os.environ.get("METRICS_TOKEN")
            token_header = request.headers.get("X-Metrics-Token")
            
            if client_ip != "127.0.0.1" and (not metrics_token or token_header != metrics_token):
                from fastapi import Response
                return Response(status_code=403, content="Forbidden")
        return await call_next(request)

    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app)

    # ── Register routers ────────────────────────────────────────────
    from aegisVault.app.routers.query  import router as query_router
    from aegisVault.app.routers.ingest import router as ingest_router
    from aegisVault.app.routers.events import router as events_router
    from aegisVault.app.routers.auth   import router as auth_router

    app.include_router(query_router,  prefix="/query",  tags=["Query"])
    app.include_router(ingest_router, prefix="/ingest", tags=["Ingest"])
    app.include_router(events_router, prefix="/events", tags=["Events"])
    app.include_router(auth_router,   prefix="/auth",   tags=["Auth"])

    # ── UI Serving ──────────────────────────────────────────────────
    @app.get("/", response_class=HTMLResponse, tags=["UI"])
    async def index(request: Request):
        is_prod = os.environ.get("APP_ENV") == "production"
        dist_dir = os.path.abspath(os.path.join(BASE_DIR, "../../../frontend/dist"))
        if is_prod:
            from fastapi.responses import FileResponse
            index_path = os.path.join(dist_dir, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
        return templates.TemplateResponse(request=request, name="index.html")

    @app.get("/health", tags=["System"])
    def health(request: Request):
        from aegisVault.db.session import health_check
        import time
        import redis
        
        db_start = time.time()
        db_ok = health_check()
        db_lat = int((time.time() - db_start) * 1000)
        
        vs = getattr(request.app.state, "vectorstore", None)
        try:
            doc_count = vs._collection.count() if vs else 0
            vs_ok = True
        except Exception:
            doc_count = 0
            vs_ok = False
            
        neo4j_ok = getattr(request.app.state, "graph", None) is not None
        
        try:
            r = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
            redis_start = time.time()
            r.ping()
            redis_lat = int((time.time() - redis_start) * 1000)
            redis_ok = True
        except Exception:
            redis_lat = 0
            redis_ok = False
            
        all_ok = db_ok and vs_ok and redis_ok
        return {
            "status":   "ok" if all_ok else "degraded",
            "version":  "1.0.0",
            "checks": {
                "db":         {"status": "ok" if db_ok else "unavailable", "latency_ms": db_lat},
                "redis":      {"status": "ok" if redis_ok else "unavailable", "latency_ms": redis_lat},
                "neo4j":      {"status": "ok" if neo4j_ok else "unavailable"},
                "vectorstore":{"status": "ok" if vs_ok else "unavailable", "doc_count": doc_count},
                "llm_client": {"status": "configured" if getattr(request.app.state, "llm_client", None) else "unavailable"}
            }
        }

    @app.get("/ready", tags=["System"])
    def ready(request: Request):
        from fastapi import Response
        from aegisVault.db.session import health_check
        import redis
        
        db_ok = health_check()
        try:
            r = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
            r.ping()
            redis_ok = True
        except Exception:
            redis_ok = False
            
        vs = getattr(request.app.state, "vectorstore", None)
        vs_ok = vs is not None
        if db_ok and redis_ok and vs_ok:
            return Response(status_code=200, content="OK")
        return Response(status_code=503, content="Service Unavailable")

    @app.get("/live", tags=["System"])
    def live():
        from fastapi import Response
        return Response(status_code=200, content="OK")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
