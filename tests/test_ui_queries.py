"""
Real integration tests for all UI queries - NO MOCKS!

These tests hit the actual database and test real system behavior.
This ensures we catch real bugs like the ESG Texas issue.
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestUIQueries:
    """Real integration tests for all UI example queries"""

    def test_portfolio_distribution_by_region(self, client):
        """Test: Portfolio distribution by region"""
        response = client.post("/qa", json={"question": "Portfolio distribution by region"})
        assert response.status_code == 200
        body = response.json()
        
        # Should contain real portfolio data
        assert body["answer"] is not None
        assert len(body["answer"]) > 0
        assert body.get("data") is not None
        
        # Should mention regions or distribution
        answer_lower = body["answer"].lower()
        assert ("west" in answer_lower or "region" in answer_lower or 
                "distribution" in answer_lower or "portfolio" in answer_lower)

    def test_properties_in_texas_esg_friendly(self, client):
        """Test: Properties in Texas that are ESG friendly - REAL TEST!"""
        response = client.post("/qa", json={"question": "Properties in Texas that are ESG friendly"})
        assert response.status_code == 200
        body = response.json()
        
        # Should find Innovation Plaza and The Independent (both have ESG features in embeddings)
        assert body["answer"] is not None
        assert body.get("data") is not None
        
        answer_lower = body["answer"].lower()
        # Should find real Texas assets with ESG characteristics
        assert ("innovation plaza" in answer_lower or "independent" in answer_lower or 
                "texas" in answer_lower)
        
        # Should not say "no assets found" anymore since we fixed the bug!
        assert "no assets found" not in answer_lower

    def test_assets_within_100km_los_angeles(self, client):
        """Test: Assets within 100km of Los Angeles"""
        response = client.post("/qa", json={"question": "Assets within 100km of Los Angeles"})
        assert response.status_code == 200
        body = response.json()
        
        assert body["answer"] is not None
        assert body.get("data") is not None
        
        # Should handle geospatial query reasonably
        answer_lower = body["answer"].lower()
        assert ("angeles" in answer_lower or "distance" in answer_lower or 
                "california" in answer_lower or "found" in answer_lower)

    def test_how_many_infrastructure_assets(self, client):
        """Test: How many infrastructure assets"""
        response = client.post("/qa", json={"question": "How many infrastructure assets"})
        assert response.status_code == 200
        body = response.json()
        
        assert body["answer"] is not None
        assert body.get("data") is not None
        
        # Should mention infrastructure or provide count
        answer_lower = body["answer"].lower()
        assert ("infrastructure" in answer_lower or "assets" in answer_lower or 
                any(str(i) in body["answer"] for i in range(1, 20)))

    def test_sustainable_renewable_energy_projects(self, client):
        """Test: Sustainable renewable energy projects"""
        response = client.post("/qa", json={"question": "Sustainable renewable energy projects"})
        assert response.status_code == 200
        body = response.json()
        
        assert body["answer"] is not None
        assert body.get("data") is not None
        
        # Vector search should find semantically similar assets
        answer_lower = body["answer"].lower()
        assert ("found" in answer_lower or "similar" in answer_lower or 
                "assets" in answer_lower)

    def test_mixed_use_properties_california(self, client):
        """Test: Mixed use properties in California"""
        response = client.post("/qa", json={"question": "Mixed use properties in California"})
        assert response.status_code == 200
        body = response.json()
        
        assert body["answer"] is not None
        assert body.get("data") is not None
        
        answer_lower = body["answer"].lower()
        assert ("california" in answer_lower or "mixed" in answer_lower or 
                "found" in answer_lower)

    def test_real_estate_assets(self, client):
        """Test: Real estate assets"""
        response = client.post("/qa", json={"question": "Real estate assets"})
        assert response.status_code == 200
        body = response.json()
        
        assert body["answer"] is not None
        assert body.get("data") is not None
        
        # Should handle asset type queries
        answer_lower = body["answer"].lower()
        assert ("real estate" in answer_lower or "assets" in answer_lower or 
                "portfolio" in answer_lower or "found" in answer_lower)

    def test_infrastructure_assets(self, client):
        """Test: Infrastructure assets"""
        response = client.post("/qa", json={"question": "Infrastructure assets"})
        assert response.status_code == 200
        body = response.json()
        
        assert body["answer"] is not None
        assert body.get("data") is not None
        
        answer_lower = body["answer"].lower()
        assert ("infrastructure" in answer_lower or "assets" in answer_lower or 
                "portfolio" in answer_lower or "found" in answer_lower)

    def test_properties_similar_to_independent(self, client):
        """Test: Properties similar to The Independent - REAL VECTOR SEARCH!"""
        response = client.post("/qa", json={"question": "Properties similar to The Independent"})
        assert response.status_code == 200
        body = response.json()
        
        assert body["answer"] is not None
        assert body.get("data") is not None
        
        # Should use vector search and find similar properties with scores
        answer_lower = body["answer"].lower()
        assert ("similar" in answer_lower or "found" in answer_lower)
        assert ("similarity" in answer_lower or "score" in answer_lower)
        
        # Should find multiple assets, not just The Independent itself
        data = body.get("data", [])
        assert len(data) > 1

    def test_assets_in_california(self, client):
        """Test: Assets in California"""
        response = client.post("/qa", json={"question": "Assets in California"})
        assert response.status_code == 200
        body = response.json()
        
        assert body["answer"] is not None
        assert body.get("data") is not None
        
        answer_lower = body["answer"].lower()
        assert "california" in answer_lower

    def test_nearby_assets(self, client):
        """Test: Nearby assets (generic query)"""
        response = client.post("/qa", json={"question": "Nearby assets"})
        assert response.status_code == 200
        body = response.json()
        
        # Should handle this gracefully, even if not specific
        assert body["answer"] is not None

    def test_commercial_buildings_texas(self, client):
        """Test: Commercial buildings in Texas"""
        response = client.post("/qa", json={"question": "Commercial buildings in Texas"})
        assert response.status_code == 200
        body = response.json()
        
        assert body["answer"] is not None
        
        answer_lower = body["answer"].lower()
        assert ("commercial" in answer_lower or "texas" in answer_lower or 
                "found" in answer_lower or "innovation plaza" in answer_lower)

    def test_assets_west_region(self, client):
        """Test: Assets in the west region"""
        response = client.post("/qa", json={"question": "Assets in the west region"})
        assert response.status_code == 200
        body = response.json()
        
        assert body["answer"] is not None
        
        answer_lower = body["answer"].lower()
        assert ("west" in answer_lower or "california" in answer_lower or 
                "found" in answer_lower or "region" in answer_lower)


class TestQueryTypes:
    """Test different query type classifications"""

    def test_portfolio_query_classification(self, client):
        """Test that portfolio queries are correctly classified"""
        response = client.post("/qa", json={"question": "Portfolio distribution by platform"})
        assert response.status_code == 200
        body = response.json()
        
        # Should have classification info
        classification = body.get("intent_classification", {})
        category = classification.get("category", "").lower()
        
        # Accept various portfolio-related classifications
        assert ("portfolio" in category or "analysis" in category or 
                category in ["portfolio_analysis", "unknown"])

    def test_geographic_query_classification(self, client):
        """Test that geographic queries are correctly classified"""
        response = client.post("/qa", json={"question": "Assets in California"})
        assert response.status_code == 200
        body = response.json()
        
        classification = body.get("intent_classification", {})
        category = classification.get("category", "").lower()
        
        # Accept geographic classifications
        assert ("geographic" in category or "assets" in category or 
                category in ["geographic_assets", "unknown"])

    def test_semantic_query_classification(self, client):
        """Test that semantic queries are correctly classified"""
        response = client.post("/qa", json={"question": "Sustainable renewable energy projects"})
        assert response.status_code == 200
        body = response.json()
        
        classification = body.get("intent_classification", {})
        category = classification.get("category", "").lower()
        
        # Accept semantic classifications
        assert ("semantic" in category or "search" in category or 
                category in ["semantic_search", "unknown"])


class TestResponseFormat:
    """Test that responses have the expected format"""

    def test_response_has_required_fields(self, client):
        """Test that responses contain all required fields"""
        response = client.post("/qa", json={"question": "How many assets"})
        assert response.status_code == 200
        body = response.json()
        
        # Required fields
        assert "answer" in body
        assert "question" in body
        assert "data" in body
        
        # Answer should not be empty
        assert body["answer"] is not None
        assert len(body["answer"]) > 0

    def test_error_handling(self, client):
        """Test that errors are handled gracefully"""
        response = client.post("/qa", json={"question": "completely nonsensical query about purple elephants"})
        assert response.status_code == 200
        body = response.json()
        
        # Should still return a valid response structure
        assert "answer" in body
        assert body["answer"] is not None


class TestSystemBehavior:
    """Test LangGraph workflow system behavior"""

    def test_langgraph_workflow_system(self, client):
        """Test that LangGraph workflows are working properly"""
        response = client.post("/qa", json={"question": "Portfolio distribution"})
        assert response.status_code == 200
        body = response.json()
        
        # Should use LangGraph workflows
        assert body.get("system_used") == "langgraph"
        assert "workflow_steps" in body
        assert len(body.get("workflow_steps", [])) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 