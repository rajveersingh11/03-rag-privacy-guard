"""
AegisVault Utils
-----------------
Shared helper functions used across all modules.
"""

from src.aegisVault.utils.common import (
    get_logger,
    hash_text,
    ensure_dir,
    sensitivity_index,
    mask_secret,
    flatten_dict,
)

__all__ = [
    "get_logger",
    "hash_text",
    "ensure_dir",
    "sensitivity_index",
    "mask_secret",
    "flatten_dict",
]