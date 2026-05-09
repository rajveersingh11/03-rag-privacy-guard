"""
Privacy Math — Layer 1 (Differential Privacy)
----------------------------------------------
Wraps any embedding model to inject calibrated Laplacian noise
BEFORE vectors are stored in the vector database.

Why: High-dimensional embeddings can be reverse-engineered via
embedding inversion attacks to reconstruct original plaintext.
DP noise guarantees reconstruction is mathematically infeasible
even if the Chroma/FAISS database is fully compromised.

Reference: PDF Section 1.2 — DPEmbedder reference implementation.
"""

import numpy as np
from typing import List
from src.aegisVault.utils.common import get_logger

logger = get_logger(__name__)


class DPEmbedder:
    """
    Wraps any LangChain-compatible embedder to add Laplacian DP noise.

    Args:
        base_embedder:  Any embedder with .embed_documents() + .embed_query()
        epsilon:        Privacy budget (from params.yaml). Lower = more private.
        sensitivity:    L2 sensitivity of the embedding function. Default 1.0.
    """

    def __init__(self, base_embedder, epsilon: float = 1.0, sensitivity: float = 1.0):
        self.base_embedder = base_embedder
        self.epsilon = epsilon
        self.sensitivity = sensitivity
        self._validate()
        logger.info(f"DPEmbedder initialised | epsilon={epsilon} | sensitivity={sensitivity}")

    # ── Core noise injection ───────────────────────────────────────────

    def _add_laplacian_noise(self, vector: np.ndarray) -> np.ndarray:
        """
        Injects Laplacian noise: noise ~ Lap(0, sensitivity/epsilon).
        The noise scale is calibrated to the privacy budget.
        """
        scale = self.sensitivity / self.epsilon
        noise = np.random.laplace(loc=0.0, scale=scale, size=vector.shape)
        return vector + noise

    # ── LangChain Embeddings interface ────────────────────────────────

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate DP-noised embeddings for a list of document chunks."""
        raw_embeddings = self.base_embedder.embed_documents(texts)
        dp_embeddings = []

        for i, emb in enumerate(raw_embeddings):
            vec = np.array(emb, dtype=np.float64)
            noisy = self._add_laplacian_noise(vec)

            noise_magnitude = float(np.linalg.norm(noisy - vec))
            logger.debug(f"Chunk {i}: noise_magnitude={noise_magnitude:.6f}")

            dp_embeddings.append(noisy.tolist())

        return dp_embeddings

    def embed_query(self, text: str) -> List[float]:
        """
        Query embeddings are NOT noised — noise only protects stored data,
        and adding noise to queries would degrade retrieval accuracy.
        """
        return self.base_embedder.embed_query(text)

    # ── Noise audit (for compliance reporting) ─────────────────────────

    def compute_noise_stats(self, original: List[float], noisy: List[float]) -> dict:
        orig_np  = np.array(original)
        noisy_np = np.array(noisy)
        diff     = noisy_np - orig_np
        return {
            "epsilon":         self.epsilon,
            "noise_l2_norm":   round(float(np.linalg.norm(diff)), 6),
            "noise_mean":      round(float(np.mean(diff)), 6),
            "noise_std":       round(float(np.std(diff)), 6),
            "cosine_sim":      round(float(
                np.dot(orig_np, noisy_np) /
                (np.linalg.norm(orig_np) * np.linalg.norm(noisy_np) + 1e-10)
            ), 6),
        }

    def _validate(self):
        if self.epsilon <= 0:
            raise ValueError(f"epsilon must be > 0, got {self.epsilon}")
        if self.sensitivity <= 0:
            raise ValueError(f"sensitivity must be > 0, got {self.sensitivity}")