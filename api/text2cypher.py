from __future__ import annotations

from functools import lru_cache
import os

from ps_genai_agents.workflows import Text2Cypher

from .config import Settings, get_driver


@lru_cache
def get_text2cypher_workflow() -> Text2Cypher:
    """Return a cached Text2Cypher workflow instance."""
    driver = get_driver()
    settings = Settings()
    return Text2Cypher(
        driver=driver,
        database=settings.neo4j_db,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )
