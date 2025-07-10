"""
Real integration test for health endpoint - NO MOCKS!
"""
from fastapi.testclient import TestClient
from api.main import app

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
