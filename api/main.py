from __future__ import annotations

import os
import json
from datetime import date, datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from neo4j.time import Date as Neo4jDate, DateTime as Neo4jDateTime

from .graphrag import create_graphrag
from .config import Settings, get_driver


def serialize_neo4j_types(obj):
    """Convert Neo4j types to JSON-serializable types."""
    if isinstance(obj, (Neo4jDate, Neo4jDateTime)):
        return str(obj)
    elif isinstance(obj, (date, datetime)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: serialize_neo4j_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [serialize_neo4j_types(item) for item in obj]
    return obj

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
async def health() -> dict[str, object]:
    """Health check that verifies Neo4j connectivity."""
    try:
        driver = get_driver()
        settings = Settings()
        async with driver.session(database=settings.neo4j_db) as session:
            result = await session.run("MATCH (n) RETURN count(n) AS count")
            record = await result.single()
            count = record["count"] if record else 0
            
        return {
            "status": "ok",
            "database": {
                "neo4j": {
                    "status": "healthy",
                    "can_connect": True,
                    "node_count": count
                }
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "database": {
                "neo4j": {
                    "status": "error",
                    "can_connect": False,
                    "error": str(e)
                }
            }
        }


class QARequest(BaseModel):
    question: str


@app.post("/qa")
async def qa(req: QARequest) -> dict[str, object]:
    """Answer a natural language question using intelligent GraphRAG with LangGraph workflows."""
    try:
        graphrag = await get_graphrag()
        result = await graphrag.answer_question(req.question)
        
        # Serialize Neo4j types to avoid serialization errors
        serialized_result = serialize_neo4j_types(result)
        return serialized_result
        
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/workflow-diagram")
async def generate_workflow_diagram() -> dict[str, str]:
    """Generate and return path to the LangGraph workflow diagram."""
    try:
        graphrag = await get_graphrag()
        output_path = "docs/workflows/langgraph_workflow.png"
        graphrag.generate_workflow_diagram(output_path)
        return {
            "status": "success",
            "diagram_path": output_path,
            "message": "Workflow diagram generated successfully"
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate diagram: {str(exc)}")
