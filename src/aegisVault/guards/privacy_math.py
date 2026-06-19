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
from aegisVault.utils.common import get_logger

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
        Ensure vectors are normalized to unit length so that cosine similarity
        in ChromaDB/FAISS remains mathematically valid.
        """
        # Ensure vector is normalized to unit length before adding noise
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        scale = self.sensitivity / self.epsilon
        noise = np.random.laplace(loc=0.0, scale=scale, size=vector.shape)
        noisy = vector + noise

        # Re-normalize to unit length for valid cosine distance calculations
        noisy_norm = np.linalg.norm(noisy)
        if noisy_norm > 0:
            return noisy / noisy_norm
        return noisy

    # ── LangChain Embeddings interface ────────────────────────────────

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate DP-noised embeddings for a list of document chunks."""
        raw_embeddings = self.base_embedder.embed_documents(texts)
        dp_embeddings = []
        
        l2_norms = []
        cosine_sims = []

        for i, emb in enumerate(raw_embeddings):
            vec = np.array(emb, dtype=np.float64)
            noisy = self._add_laplacian_noise(vec)
            noisy_list = noisy.tolist()

            stats = self.compute_noise_stats(emb, noisy_list)
            l2_norms.append(stats["noise_l2_norm"])
            cosine_sims.append(stats["cosine_sim"])

            logger.debug(f"Chunk {i}: noise_magnitude={stats['noise_l2_norm']:.6f}")
            dp_embeddings.append(noisy_list)

        # Audit DP statistics to database
        if len(raw_embeddings) > 0:
            try:
                import uuid
                from sqlalchemy import text
                from aegisVault.db.session import db_session
                
                mean_l2 = float(np.mean(l2_norms))
                mean_cos = float(np.mean(cosine_sims))
                
                stmt = text("""
                    INSERT INTO dp_audit (id, doc_id, epsilon, sensitivity, noise_l2_mean, cosine_sim_mean, chunks_processed)
                    VALUES (:id, :doc_id, :epsilon, :sensitivity, :noise_l2_mean, :cosine_sim_mean, :chunks_processed)
                """)
                
                with db_session() as session:
                    session.execute(stmt, {
                        "id": str(uuid.uuid4()),
                        "doc_id": "unknown",  # doc_id is not directly exposed to embedder, can be correlated via timestamp
                        "epsilon": self.epsilon,
                        "sensitivity": self.sensitivity,
                        "noise_l2_mean": mean_l2,
                        "cosine_sim_mean": mean_cos,
                        "chunks_processed": len(raw_embeddings)
                    })
            except Exception as e:
                logger.error(f"Failed to log DP audit stats to DB: {e}")

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