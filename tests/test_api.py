from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


class DummyResult:
    async def single(self):
        return [0]

    async def data(self):
        return []


class DummySession:
    async def run(self, *_args, **_kwargs):
        return DummyResult()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        pass


class DummyDriver:
    def session(self, **_kwargs):
        return DummySession()


def _set_env(monkeypatch) -> None:
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost")
    monkeypatch.setenv("NEO4J_USERNAME", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "test")


def test_health(monkeypatch) -> None:
    _set_env(monkeypatch)
    monkeypatch.setattr("api.main.get_driver", lambda: DummyDriver())
    monkeypatch.setattr("api.graphrag.get_driver", lambda: DummyDriver())
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200


def test_qa(monkeypatch) -> None:
    _set_env(monkeypatch)
    monkeypatch.setattr("api.main.get_driver", lambda: DummyDriver())
    monkeypatch.setattr("api.graphrag.get_driver", lambda: DummyDriver())
    client = TestClient(app)
    resp = client.post("/qa", json={"question": "asset count"})
    assert resp.status_code == 200
