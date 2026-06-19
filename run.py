#!/usr/bin/env python3
"""
AegisVault Unified Stack Orchestrator
-------------------------------------
Serves as the single entry point for development, testing, and production serving.
Automates Docker services, Python pathing, OS-specific Celery workers, and Vite frontend.
"""

import os
import sys
import subprocess
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Ensure we read environment variables
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent
PYTHONPATH = str(PROJECT_ROOT / "src")

# Colors for pretty terminal logs
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"


def log_info(msg: str):
    print(f"{BLUE}[INFO]{RESET} {msg}")


def log_success(msg: str):
    print(f"{GREEN}[SUCCESS]{RESET} {msg}")


def log_warning(msg: str):
    print(f"{YELLOW}[WARNING]{RESET} {msg}")


def log_error(msg: str):
    print(f"{RED}[ERROR]{RESET} {msg}")


def run_command(cmd: list, cwd: Path = PROJECT_ROOT, env: dict = None) -> int:
    """Helper to run a blocking shell command."""
    try:
        res = subprocess.run(cmd, cwd=cwd, env=env)
        return res.returncode
    except Exception as e:
        log_error(f"Failed to run command {cmd}: {e}")
        return 1


def check_docker() -> bool:
    """Verifies docker daemon is running."""
    try:
        res = subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False


def start_backing_services():
    """Brings up docker-compose backing services."""
    if not check_docker():
        log_error("Docker is not running or not installed. Backing services (Redis, Neo4j, MySQL, Chroma) cannot start.")
        sys.exit(1)

    log_info("Starting backing services via Docker Compose...")
    ret = run_command(["docker", "compose", "up", "-d"])
    if ret != 0:
        log_error("Failed to start docker backing services.")
        sys.exit(1)
    log_success("Backing services are up and healthy!")


def stop_backing_services():
    """Brings down docker-compose backing services."""
    if check_docker():
        log_info("Stopping backing services...")
        run_command(["docker", "compose", "down"])
        log_success("Backing services stopped.")
    else:
        log_warning("Docker is not running; skipping compose down.")


def build_frontend():
    """Compiles the frontend assets."""
    log_info("Building production frontend...")
    npm_cmd = "npm.cmd" if sys.platform.startswith("win") else "npm"
    # Ensure dependencies are synced
    run_command([npm_cmd, "install"], cwd=PROJECT_ROOT / "frontend")
    ret = run_command([npm_cmd, "run", "build"], cwd=PROJECT_ROOT / "frontend")
    if ret != 0:
        log_error("Frontend build failed.")
        sys.exit(1)
    log_success("Frontend build succeeded!")


def run_stack(mode: str = "dev"):
    """Spins up all required processes in parallel and monitors them."""
    start_backing_services()

    env = os.environ.copy()
    env["PYTHONPATH"] = PYTHONPATH

    processes = []
    
    npm_cmd = "npm.cmd" if sys.platform.startswith("win") else "npm"

    try:
        # 1. Start Celery Worker
        log_info("Starting Celery asynchronous worker...")
        celery_cmd = ["celery", "-A", "aegisVault.worker", "worker", "--loglevel=info"]
        if sys.platform.startswith("win"):
            # Use solo pool on Windows to prevent billiard multiprocessing errors
            celery_cmd += ["-P", "solo"]
        else:
            celery_cmd += ["--concurrency=4"]
        
        celery_proc = subprocess.Popen(celery_cmd, cwd=PROJECT_ROOT, env=env)
        processes.append(("Celery Worker", celery_proc))

        # 2. Start FastAPI server
        log_info("Starting FastAPI API Gateway...")
        fastapi_cmd = ["uvicorn", "aegisVault.app.main:app", "--port", "8000", "--host", "0.0.0.0"]
        if mode == "dev":
            fastapi_cmd += ["--reload"]
            env["APP_ENV"] = "development"
        else:
            env["APP_ENV"] = "production"

        fastapi_proc = subprocess.Popen(fastapi_cmd, cwd=PROJECT_ROOT, env=env)
        processes.append(("FastAPI Backend", fastapi_proc))

        # 3. Start Frontend (Vite) Dev Server if in dev mode
        if mode == "dev":
            log_info("Starting Vite frontend development server...")
            # Ensure node_modules exists
            if not (PROJECT_ROOT / "frontend" / "node_modules").exists():
                log_info("node_modules missing in frontend folder. Running npm install...")
                subprocess.run([npm_cmd, "install"], cwd=PROJECT_ROOT / "frontend")
            
            vite_proc = subprocess.Popen([npm_cmd, "run", "dev"], cwd=PROJECT_ROOT / "frontend")
            processes.append(("Vite Frontend", vite_proc))
            log_success(f"Dev Stack Running! API: http://localhost:8000/docs | UI: http://localhost:5173/")
        else:
            log_success(f"Production Stack Serving! Unified interface: http://localhost:8000/")

        # Monitor processes
        log_info("Press Ctrl+C to stop all services.")
        while True:
            time.sleep(1)
            for name, proc in processes:
                if proc.poll() is not None:
                    # Process crashed or terminated
                    log_error(f"Process [{name}] exited unexpectedly with code {proc.returncode}.")
                    raise KeyboardInterrupt()

    except KeyboardInterrupt:
        print("\n")
        log_warning("Shutting down processes cleanly...")
    finally:
        # Kill all spawned processes
        for name, proc in processes:
            if proc.poll() is None:
                log_info(f"Terminating {name}...")
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    log_warning(f"Force-killing {name}...")
                    proc.kill()
                except Exception as e:
                    log_error(f"Error terminating {name}: {e}")
        log_success("All processes terminated successfully.")


def main():
    parser = argparse.ArgumentParser(description="AegisVault Command Center Runner")
    parser.add_argument(
        "action",
        choices=["dev", "prod", "stop", "test"],
        default="dev",
        nargs="?",
        help="Action to perform: 'dev' (run local dev servers), 'prod' (build UI and serve), 'stop' (docker compose down), 'test' (run pytest)"
    )
    args = parser.parse_args()

    if args.action == "dev":
        run_stack(mode="dev")
    elif args.action == "prod":
        build_frontend()
        run_stack(mode="prod")
    elif args.action == "stop":
        stop_backing_services()
    elif args.action == "test":
        log_info("Running project security test suite...")
        env = os.environ.copy()
        env["PYTHONPATH"] = PYTHONPATH
        run_command(["pytest"], env=env)


if __name__ == "__main__":
    main()
