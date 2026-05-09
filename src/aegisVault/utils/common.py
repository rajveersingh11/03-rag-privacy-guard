"""Shared utilities used across AegisVault."""

import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List


import logging.handlers
from datetime import datetime

# Global flag to ensure logging is only setup once
_LOGGING_INITIALIZED = False

def get_logger(name: str) -> logging.Logger:
    """
    Returns a pre-configured logger instance.
    
    Why the previous version might not have been working:
    1. logging.basicConfig(...) only configures the root logger ONCE. 
       Subsequent calls do nothing.
    2. No FileHandler was configured, so logs only went to the console.
    3. The format was fixed and didn't allow for project-wide overrides.
    """
    global _LOGGING_INITIALIZED
    
    logger = logging.getLogger(name)
    
    if not _LOGGING_INITIALIZED:
        _setup_initial_logging()
        _LOGGING_INITIALIZED = True
        
    return logger

def _setup_initial_logging():
    """Sets up the root logger with both Stream and File handlers."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clean existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    formatter = logging.Formatter(log_format)
    
    # 1. Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 2. File Handler (Attempt to use config path, fallback to ./logs)
    try:
        # Avoid circular import by importing inside function
        from src.aegisVault.config.manager import get_config
        cfg = get_config()
        log_dir = Path(cfg.paths.audit_log_dir)
    except Exception:
        log_dir = Path("logs")
        
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"aegisvault_{datetime.now().strftime('%Y%m%d')}.log"
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    root_logger.info(f"Logging initialized. File: {log_file}")


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def sensitivity_index(level: str) -> int:
    from src.aegisVault.constants import SENSITIVITY_LEVELS
    return SENSITIVITY_LEVELS.index(level) if level in SENSITIVITY_LEVELS else 0


def mask_secret(value: str, show_chars: int = 4) -> str:
    """Return partially masked string for safe logging."""
    if len(value) <= show_chars:
        return "***"
    return value[:show_chars] + "***"


def flatten_dict(d: Dict, parent_key: str = "", sep: str = ".") -> Dict:
    items: List = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    return dict(items)