from fastapi.testclient import TestClient
from api.main import app

class DummyResult:
    async def single(self):
        return {"count": 0}

class DummySession:
    async def run(self, *args, **kwargs):
        return DummyResult()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

class DummyDriver:
    def session(self, database=None):
        return DummySession()

def test_health_endpoint(monkeypatch):
    monkeypatch.setattr("api.main.get_driver", lambda: DummyDriver())
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
