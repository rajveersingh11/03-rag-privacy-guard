"""Shared utilities used across AegisVault."""

import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List


def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    return logging.getLogger(name)


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