from fastapi.testclient import TestClient

from api.main import app
import api.graphrag as graphrag


class DummyResult:
    def __init__(self, data):
        self._data = data

    async def data(self):
        return self._data

    async def single(self):
        return self._data[0] if self._data else None


class DummySession:
    def __init__(self, mapping):
        self.mapping = mapping
        self.last_query = None
        self.last_params = None

    async def run(self, cypher, params=None):
        self.last_query = cypher
        self.last_params = params or {}
        data = self.mapping.get(cypher.strip(), [])
        return DummyResult(data)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass


class DummyDriver:
    def __init__(self, session):
        self.session_obj = session

    def session(self, database=None):
        return self.session_obj


UNEMPLOYMENT_CA_CYPHER = (
    """MATCH (mt:MetricType {name: \"California Unemployment Rate\"})-[:TAIL]->(latest:MetricValue)
           RETURN \"California\" AS state,
                  latest.value AS unemployment_rate,
                  latest.date AS as_of_date,
                  mt.name AS metric_name"""
)

ASSETS_STATE_CYPHER = (
    """MATCH (a:Asset)-[:LOCATED_IN]->(c:City)-[:PART_OF]->(s:State {name: $normalized_state})
           RETURN a.name AS asset_name, c.name AS city,
                  a.building_type AS building_type"""
)

INTEREST_RATES_CYPHER = (
    """MATCH (mt:MetricType)-[:TAIL]->(latest:MetricValue)
           WHERE mt.category = \"Interest Rate\"
           RETURN mt.name AS rate_type,
                  latest.value AS current_rate,
                  latest.date AS as_of_date
           ORDER BY mt.name"""
)


def setup_driver(monkeypatch, mapping):
    session = DummySession(mapping)
    driver = DummyDriver(session)
    monkeypatch.setattr("api.main.get_driver", lambda: driver)
    monkeypatch.setattr("api.graphrag.get_driver", lambda: driver)
    return session


def test_unemployment_california(monkeypatch):
    data = [
        {
            "state": "California",
            "unemployment_rate": 4.5,
            "as_of_date": "2025-01-01",
            "metric_name": "California Unemployment Rate",
        }
    ]
    session = setup_driver(monkeypatch, {UNEMPLOYMENT_CA_CYPHER.strip(): data})

    client = TestClient(app)
    response = client.post("/qa", json={"question": "unemployment rate in California"})
    assert response.status_code == 200
    body = response.json()
    assert body["pattern_matched"] is True
    assert session.last_query is not None


def test_assets_in_texas(monkeypatch):
    data = [
        {"asset_name": "Tower", "city": "Dallas", "building_type": "office"},
        {"asset_name": "Plaza", "city": "Austin", "building_type": "retail"},
    ]
    session = setup_driver(monkeypatch, {ASSETS_STATE_CYPHER.strip(): data})

    client = TestClient(app)
    response = client.post("/qa", json={"question": "assets in Texas"})
    assert response.status_code == 200
    body = response.json()
    assert body["pattern_matched"] is True
    assert session.last_query is not None


def test_current_interest_rates(monkeypatch):
    data = [
        {"rate_type": "30-Year Mortgage Rate", "current_rate": 6.5, "as_of_date": "2025-07-03"},
        {"rate_type": "Federal Funds Rate", "current_rate": 4.33, "as_of_date": "2025-06-01"},
    ]
    session = setup_driver(monkeypatch, {INTEREST_RATES_CYPHER.strip(): data})

    client = TestClient(app)
    response = client.post("/qa", json={"question": "current interest rates"})
    assert response.status_code == 200
    body = response.json()
    assert body["pattern_matched"] is True
    assert session.last_query is not None


def test_llm_fallback(monkeypatch):
    session = setup_driver(monkeypatch, {})

    called = {}

    async def dummy_fallback(question: str):
        called["q"] = question
        return {
            "answer": "fallback",
            "cypher": None,
            "data": [],
            "question": question,
            "pattern_matched": False,
            "llm_fallback": True,
        }

    monkeypatch.setattr(graphrag, "llm_fallback", dummy_fallback)

    client = TestClient(app)
    response = client.post("/qa", json={"question": "nonsense query"})
    assert response.status_code == 200
    assert called["q"] == "nonsense query"
    body = response.json()
    assert body["pattern_matched"] is False
    assert body.get("llm_fallback") is True
