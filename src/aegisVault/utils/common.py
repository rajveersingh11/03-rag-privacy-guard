"""Shared utilities used across AegisVault."""

import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List


import logging.handlers
from datetime import datetime

import contextvars
from pythonjsonlogger import jsonlogger
import colorlog

# Context vars for structured logging
trace_id_ctx = contextvars.ContextVar("trace_id", default="")
tenant_id_ctx = contextvars.ContextVar("tenant_id", default="")
user_id_ctx = contextvars.ContextVar("user_id", default="")

# Global flag to ensure logging is only setup once
_LOGGING_INITIALIZED = False

class ContextFilter(logging.Filter):
    def filter(self, record):
        record.trace_id = trace_id_ctx.get()
        record.tenant_id = tenant_id_ctx.get()
        record.user_id = user_id_ctx.get()
        return True

def setup_logging():
    """Sets up the root logger with structured JSON or colored output."""
    global _LOGGING_INITIALIZED
    if _LOGGING_INITIALIZED:
        return
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    console_handler = logging.StreamHandler()
    console_handler.addFilter(ContextFilter())
    
    if os.environ.get("APP_ENV") == "production":
        formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(trace_id)s %(tenant_id)s %(user_id)s %(message)s',
            rename_fields={"levelname": "level", "asctime": "timestamp"}
        )
    else:
        formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s | %(levelname)-8s | [%(trace_id)s] %(name)s | %(message)s',
            log_colors={
                'DEBUG':    'cyan',
                'INFO':     'green',
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    _LOGGING_INITIALIZED = True

def get_logger(name: str) -> logging.Logger:
    """Returns a logger instance."""
    setup_logging()
    return logging.getLogger(name)

def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def sensitivity_index(level: str) -> int:
    from aegisVault.constants import SENSITIVITY_LEVELS
    return SENSITIVITY_LEVELS.index(level) if level in SENSITIVITY_LEVELS else 0


def parse_metadata_list(value: Any) -> List[str]:
    """Normalize list-like Chroma metadata stored as JSON text or scalars."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple) or isinstance(value, set):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return [item.strip() for item in raw.split(",") if item.strip()]
        return parse_metadata_list(parsed)
    return [str(value).strip()]


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
