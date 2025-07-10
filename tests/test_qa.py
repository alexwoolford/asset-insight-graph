"""
Real integration tests for QA endpoint - NO MOCKS!

These tests hit the actual database and test real system behavior.
"""
import os
import pytest
from fastapi.testclient import TestClient
from api.main import app

NEO4J_AVAILABLE = all([
    os.getenv("NEO4J_URI"),
    os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER"),
    os.getenv("NEO4J_PASSWORD"),
])

pytestmark = pytest.mark.skipif(
    not NEO4J_AVAILABLE, reason="Neo4j connection settings not provided"
)


@pytest.fixture
def client():
    return TestClient(app)


class TestQAEndpoint:
    """Real integration tests for the QA endpoint"""

    def test_geographic_query_california(self, client):
        """Test: California unemployment data query"""
        response = client.post("/qa", json={"question": "unemployment in California"})
        assert response.status_code == 200
        body = response.json()
        
        # Should contain a valid response
        assert body["answer"] is not None
        assert len(body["answer"]) > 0
        
        # Should handle unemployment/economic data queries
        answer_lower = body["answer"].lower()
        assert ("california" in answer_lower or "unemployment" in answer_lower or 
                "economic" in answer_lower or "data" in answer_lower)

    def test_assets_in_texas(self, client):
        """Test: Assets in Texas query"""
        response = client.post("/qa", json={"question": "assets in Texas"})
        assert response.status_code == 200
        body = response.json()
        
        assert body["answer"] is not None
        assert body.get("data") is not None
        
        # Should find Texas assets
        answer_lower = body["answer"].lower()
        assert "texas" in answer_lower

    def test_current_interest_rates(self, client):
        """Test: Current interest rates query"""
        response = client.post("/qa", json={"question": "current interest rates"})
        assert response.status_code == 200
        body = response.json()
        
        assert body["answer"] is not None
        
        # Should handle economic data queries
        answer_lower = body["answer"].lower()
        assert ("interest" in answer_lower or "rates" in answer_lower or 
                "economic" in answer_lower or "data" in answer_lower)

    def test_unknown_query_handling(self, client):
        """Test: Unknown query handling without mocks"""
        response = client.post("/qa", json={"question": "completely unknown query about zebras"})
        assert response.status_code == 200
        body = response.json()
        
        # Should handle gracefully and return some response
        assert body["answer"] is not None
        assert len(body["answer"]) > 0


class TestQueryValidation:
    """Test query validation and error handling"""

    def test_empty_question(self, client):
        """Test empty question handling"""
        response = client.post("/qa", json={"question": ""})
        assert response.status_code == 200
        body = response.json()
        
        # Should handle empty questions gracefully
        assert body["answer"] is not None

    def test_missing_question_field(self, client):
        """Test missing question field"""
        response = client.post("/qa", json={})
        assert response.status_code == 422  # Validation error

    def test_malformed_json(self, client):
        """Test malformed JSON request"""
        response = client.post("/qa", data="invalid json")
        assert response.status_code == 422  # Validation error


class TestSystemBehavior:
    """Test real system behavior with LangGraph workflows"""

    def test_graphrag_system(self, client):
        """Test GraphRAG system with real data"""
        response = client.post("/qa", json={"question": "How many infrastructure assets"})
        assert response.status_code == 200
        body = response.json()
        
        # Should use LangGraph workflow
        assert body.get("system_used") == "langgraph"
        assert body["answer"] is not None
        assert "workflow_steps" in body


class TestRealDatabaseConnectivity:
    """Test that we're actually hitting the real database"""

    def test_vector_search_functionality(self, client):
        """Test that vector search is actually working"""
        response = client.post("/qa", json={"question": "Properties similar to The Independent"})
        assert response.status_code == 200
        body = response.json()
        
        # Should return similarity scores (proving vector search is working)
        assert body["answer"] is not None
        answer_lower = body["answer"].lower()
        assert ("similar" in answer_lower or "similarity" in answer_lower)
        
        # Should have actual data
        data = body.get("data", [])
        assert len(data) > 0

    def test_geographic_filtering(self, client):
        """Test that geographic filtering is working"""
        response = client.post("/qa", json={"question": "Properties in California"})
        assert response.status_code == 200
        body = response.json()
        
        # Should find California assets
        assert body["answer"] is not None
        answer_lower = body["answer"].lower()
        assert "california" in answer_lower
        
        # Should have actual data from database
        data = body.get("data", [])
        assert len(data) > 0 or "found" in answer_lower

    def test_portfolio_analytics(self, client):
        """Test that portfolio analytics queries work"""
        response = client.post("/qa", json={"question": "Portfolio distribution by region"})
        assert response.status_code == 200
        body = response.json()
        
        # Should return distribution data
        assert body["answer"] is not None
        assert body.get("data") is not None
        
        # Should mention regions or distribution
        answer_lower = body["answer"].lower()
        assert ("region" in answer_lower or "distribution" in answer_lower or 
                "west" in answer_lower or "portfolio" in answer_lower)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
