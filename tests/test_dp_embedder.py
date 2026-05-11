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
