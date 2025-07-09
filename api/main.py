from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import graphrag
from .config import Settings, get_driver

app = FastAPI()


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check that verifies Neo4j connectivity."""
    driver = get_driver()
    settings = Settings()
    async with driver.session(database=settings.neo4j_db) as session:
        result = await session.run("MATCH (n) RETURN count(n) AS count")
        await result.single()
    return {"status": "ok"}


class QARequest(BaseModel):
    question: str


@app.post("/qa")
async def qa(req: QARequest) -> dict[str, object]:
    """Answer a natural language question using the graph."""
    try:
        return await graphrag.answer_geospatial(req.question)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
