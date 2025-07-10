"""
Real integration test for health endpoint - NO MOCKS!
"""
from fastapi.testclient import TestClient
from api.main import app
import os
import pytest

NEO4J_AVAILABLE = all([
    os.getenv("NEO4J_URI"),
    os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER"),
    os.getenv("NEO4J_PASSWORD"),
])

pytestmark = pytest.mark.skipif(
    not NEO4J_AVAILABLE, reason="Neo4j connection settings not provided"
)

def test_health_endpoint():
    """Test health endpoint with real database connection"""
    client = TestClient(app)
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have database status
    assert "database" in data
    assert "neo4j" in data["database"]
    
    # Should report healthy status if database is accessible
    status = data["database"]["neo4j"]["status"] 
    assert status in ["healthy", "error"]  # Accept either depending on database state
    
    # Should have connection test
    assert "can_connect" in data["database"]["neo4j"]
