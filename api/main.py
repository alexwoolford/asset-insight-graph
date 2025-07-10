from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .graphrag import create_graphrag
from .config import Settings, get_driver

app = FastAPI()

# Initialize GraphRAG system
_graphrag_instance = None

async def get_graphrag():
    """Get or create GraphRAG instance."""
    global _graphrag_instance
    if _graphrag_instance is None:
        _graphrag_instance = await create_graphrag()
    return _graphrag_instance


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
    """Answer a natural language question using intelligent GraphRAG."""
    try:
        graphrag = await get_graphrag()
        result = await graphrag.answer_question(req.question)
        return result
        
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
