import pytest
from unittest.mock import MagicMock
from aegisVault.guards.privacy_math import DPEmbedder

def test_dp_embedder_injects_noise():
    # Mock base embedder
    mock_base = MagicMock()
    mock_base.embed_documents.return_value = [[1.0, 0.0], [0.0, 1.0]]
    mock_base.embed_query.return_value = [1.0, 0.0]

    embedder = DPEmbedder(mock_base, epsilon=1.0, sensitivity=1.0)
    
    # Noise is injected into documents
    docs = embedder.embed_documents(["doc1", "doc2"])
    assert docs != [[1.0, 0.0], [0.0, 1.0]]  # Almost certainly different due to noise
    
    # Noise is NOT injected into query
    query = embedder.embed_query("test query")
    assert query == [1.0, 0.0]

def test_dp_embedder_invalid_epsilon():
    mock_base = MagicMock()
    with pytest.raises(ValueError, match="epsilon must be > 0"):
        DPEmbedder(mock_base, epsilon=-1.0, sensitivity=1.0)


def test_dp_embedder_gaussian_mechanism():
    mock_base = MagicMock()
    mock_base.embed_documents.return_value = [[10.0, 0.0]]
    embedder = DPEmbedder(
        mock_base,
        epsilon=1.0,
        mechanism="gaussian",
        delta=1e-5,
        clipping_threshold=2.0
    )
    
    docs = embedder.embed_documents(["doc1"])
    import numpy as np
    assert np.allclose(np.linalg.norm(docs[0]), 1.0)
    assert docs[0] != [1.0, 0.0]


def test_dp_embedder_clipping_bounds():
    mock_base = MagicMock()
    embedder = DPEmbedder(
        mock_base,
        epsilon=1.0,
        clipping_threshold=2.0
    )
    import numpy as np
    vec = np.array([10.0, 0.0])
    noisy_vec = embedder._add_dp_noise(vec)
    assert np.allclose(np.linalg.norm(noisy_vec), 1.0)


def test_dp_embedder_invalid_configs():
    mock_base = MagicMock()
    with pytest.raises(ValueError, match="mechanism must be"):
        DPEmbedder(mock_base, mechanism="invalid")
        
    with pytest.raises(ValueError, match="delta must be > 0"):
        DPEmbedder(mock_base, mechanism="gaussian", delta=0.0)
        
    with pytest.raises(ValueError, match="clipping_threshold must be > 0"):
        DPEmbedder(mock_base, clipping_threshold=-1.0)

