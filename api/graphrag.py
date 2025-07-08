from __future__ import annotations

import os
import re
from typing import Any, Dict, List

from .config import Settings, get_driver

RULES: List[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"assets in (?P<city>.+)", re.I),
        "MATCH (a:Asset {city:$city}) RETURN a.name AS name",
    ),
    (
        re.compile(r"partners investing in asset (?P<name>.+)", re.I),
        "MATCH (p:Partner)-[:CO_INVESTED]->(a:Asset {name:$name}) RETURN p.name AS name",
    ),
    (re.compile(r"asset count", re.I), "MATCH (a:Asset) RETURN count(a) AS count"),
]


async def answer(question: str) -> Dict[str, Any]:
    """Return answer dictionary for the given question."""
    for pattern, cypher in RULES:
        match = pattern.search(question)
        if match:
            params = match.groupdict()
            driver = get_driver()
            settings = Settings()
            async with driver.session(database=settings.neo4j_db) as session:
                result = await session.run(cypher, params)
                data = await result.data()
            return {"answer": "", "cypher": cypher, "data": data}

    if os.getenv("OPENAI_API_KEY"):
        raise NotImplementedError("LLM-based answering not implemented")
    raise NotImplementedError("No rule matched and OPENAI_API_KEY not set")
