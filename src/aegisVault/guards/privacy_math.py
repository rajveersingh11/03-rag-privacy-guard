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

    def __init__(
        self,
        base_embedder,
        epsilon: float = 1.0,
        sensitivity: float = 1.0,
        delta: float = 1e-5,
        mechanism: str = "laplace",
        clipping_threshold: float = 1.0,
    ):
        self.base_embedder = base_embedder
        self.epsilon = epsilon
        self.sensitivity = sensitivity
        self.delta = delta
        self.mechanism = mechanism
        self.clipping_threshold = clipping_threshold
        self._validate()
        logger.info(
            f"DPEmbedder initialised | epsilon={epsilon} | sensitivity={sensitivity} | "
            f"delta={delta} | mechanism={mechanism} | clipping_threshold={clipping_threshold}"
        )

    # ── Core noise injection ───────────────────────────────────────────

    def _add_dp_noise(self, vector: np.ndarray) -> np.ndarray:
        """
        Injects calibrated DP noise into the unnormalized vector using clipping.
        Supported mechanisms:
        - "laplace": adds noise ~ Lap(0, scale) where scale = clipping_threshold / epsilon.
        - "gaussian": adds noise ~ N(0, sigma^2) where sigma = clipping_threshold * sqrt(2 * ln(1.25 / delta)) / epsilon.
        
        Finally, projects the noisy vector back onto the unit sphere for cosine similarity.
        """
        # 1. Clip the unnormalized vector to the configured clipping threshold
        norm = np.linalg.norm(vector)
        if norm > self.clipping_threshold:
            vector = vector * (self.clipping_threshold / norm)

        # 2. Setup CSRNG for generating noise
        import secrets
        seed_bytes = secrets.token_bytes(16)
        seed_int = int.from_bytes(seed_bytes, "big")
        rng = np.random.default_rng(seed_int)

        # 3. Add noise based on mechanism
        if self.mechanism == "gaussian":
            if self.delta <= 0:
                raise ValueError("delta must be > 0 for Gaussian mechanism")
            sigma = (self.clipping_threshold * np.sqrt(2 * np.log(1.25 / self.delta))) / self.epsilon
            noise = rng.normal(loc=0.0, scale=sigma, size=vector.shape)
        else:  # Laplace
            scale = self.clipping_threshold / self.epsilon
            noise = rng.laplace(loc=0.0, scale=scale, size=vector.shape)

        noisy = vector + noise

        # 4. Project back onto the unit sphere for valid cosine similarity
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
            noisy = self._add_dp_noise(vec)
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
        if self.mechanism not in ("laplace", "gaussian"):
            raise ValueError(f"mechanism must be 'laplace' or 'gaussian', got {self.mechanism}")
        if self.mechanism == "gaussian" and self.delta <= 0:
            raise ValueError(f"delta must be > 0 for Gaussian mechanism, got {self.delta}")
        if self.clipping_threshold <= 0:
            raise ValueError(f"clipping_threshold must be > 0, got {self.clipping_threshold}")