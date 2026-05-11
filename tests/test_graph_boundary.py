import pytest
from unittest.mock import MagicMock
from aegisVault.guards.graph_boundary import GraphBoundary
from aegisVault.entity.config_entity import GraphConfig

@pytest.fixture
def mock_config():
    return GraphConfig(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        tenant_isolation=True,
        enforce_acl_on_nodes=True
    )

def test_get_authorized_doc_ids(mock_config, monkeypatch):
    # Mock Neo4j driver
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_session.run.return_value = [{"doc_id": "d1"}, {"doc_id": "d2"}]
    
    monkeypatch.setattr("neo4j.GraphDatabase.driver", lambda *args, **kwargs: mock_driver)

    graph = GraphBoundary(mock_config)
    doc_ids = graph.get_authorized_doc_ids(["employee"], "default", "INTERNAL")
    
    assert doc_ids == ["d1", "d2"]
    mock_session.run.assert_called_once()
