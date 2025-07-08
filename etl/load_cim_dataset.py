from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

SCHEMA_PATH = Path(__file__).with_name("schema.cypher")
DATA_PATH = Path(__file__).with_name("cim_assets.jsonl")

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


async def run_queries(driver, queries: list[str]) -> None:
    async with driver.session(database=NEO4J_DATABASE) as session:
        for q in queries:
            if q.strip():
                await session.run(q)


def parse_schema() -> list[str]:
    text = SCHEMA_PATH.read_text()
    return [stmt.strip() for stmt in text.split(";") if stmt.strip()]


def read_assets() -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    if DATA_PATH.exists():
        with DATA_PATH.open() as f:
            for line in f:
                assets.append(json.loads(line))
    return assets


async def load() -> None:
    """Load scraped CIM assets into Neo4j."""
    if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
        raise EnvironmentError("Missing Neo4j connection settings")

    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    await run_queries(driver, parse_schema())

    assets = read_assets()
    async with driver.session(database=NEO4J_DATABASE) as session:
        for row in assets:
            cypher = (
                "MERGE (a:Asset {id: $id}) SET a.name=$name, a.city=$city, a.state=$state "
                "MERGE (c:City {name:$city}) "
                "MERGE (a)-[:LOCATED_IN]->(c) "
                "MERGE (t:Type {name:$platform}) "
                "MERGE (a)-[:HAS_TYPE]->(t)"
            )
            await session.run(
                cypher,
                {
                    "id": row.get("item_id"),
                    "name": row.get("name"),
                    "city": row.get("city"),
                    "state": row.get("state"),
                    "platform": row.get("platform"),
                },
            )
    await driver.close()


if __name__ == "__main__":
    asyncio.run(load())
