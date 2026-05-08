"""
AegisVault Config
------------------
Bridges params.yaml + config.yaml → typed AegisVaultConfig object.

Usage:
    from aegisVault.config import get_config
    cfg = get_config()
    print(cfg.dp.epsilon)
"""

from aegisVault.config.manager import get_config

__all__ = ["get_config"]