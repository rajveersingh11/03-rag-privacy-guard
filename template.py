import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s: %(message)s:]')

# The New Identity
project_name = "aegisVault" 

list_of_files = [
    ".github/workflows/.gitkeep",
    f"src/{project_name}/__init__.py",
    
    # ── COMPONENTS: The "Guts" of the security logic ──────────
    f"src/{project_name}/components/__init__.py",
    f"src/{project_name}/components/ingestion_scrubber.py", # Layer 1: PII/Secret removal
    f"src/{project_name}/components/privacy_math.py",       # Layer 1: Differential Privacy (DP)
    f"src/{project_name}/components/semantic_router.py",    # Layer 2: Agentic Intent classification
    f"src/{project_name}/components/graph_boundary.py",     # Layer 3: Multi-tenant Graph isolation
    f"src/{project_name}/components/output_sanitizer.py",   # Layer 5: Canary tokens & Redaction

    # ── ENTITY: Data Classes for strict type-safety ───────────
    f"src/{project_name}/entity/__init__.py",
    f"src/{project_name}/entity/config_entity.py",          # Definitions for Epsilon/Alpha budgets
    f"src/{project_name}/entity/artifact_entity.py",        # Tracking ingestion outputs

    # ── CONFIG: The Bridge between YAML and Code ─────────────
    f"src/{project_name}/config/__init__.py",
    f"src/{project_name}/config/manager.py",                # Configuration Manager logic

    # ── PIPELINE: Coordinating the Stages ─────────────────────
    f"src/{project_name}/pipeline/__init__.py",
    f"src/{project_name}/pipeline/ingestion_pipeline.py",   # Offline Async process[cite: 1]
    f"src/{project_name}/pipeline/inference_pipeline.py",   # Real-time guarded query[cite: 1]

    # ── CONSTANTS & UTILS ─────────────────────────────────────
    f"src/{project_name}/constants/__init__.py",
    f"src/{project_name}/utils/__init__.py",
    f"src/{project_name}/utils/common.py",

    # ── ROOT LEVEL: Deployment & Metadata ─────────────────────
    "config/config.yaml",    # File paths and environment settings
    "params.yaml",           # DP Epsilon, Top-K, model_ids[cite: 1]
    "app.py",                # FastAPI entry point
    "worker.py",             # Celery/Redis worker for Layer 1[cite: 1]
    "setup.py",              # Makes AegisVault pip-installable
    "requirements.txt",
    "docker-compose.yaml",   # Spins up App + Redis + Postgres + GraphDB[cite: 1]
    "research/prototypes.ipynb"
]

for filepath in list_of_files:
    filepath = Path(filepath)
    filedir, filename = os.path.split(filepath)

    if filedir != "":
        os.makedirs(filedir, exist_ok=True)
        logging.info(f"Creating directory: {filedir} for the file: {filename}")

    if (not os.path.exists(filepath)) or (os.path.getsize(filepath) == 0):
        with open(filepath, "w") as f:
            pass
            logging.info(f"Creating empty file: {filepath}")