from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

SCHEMA_PATH = Path(__file__).with_name("schema.cypher")
DATA_PATH = Path(__file__).with_name("data") / "sample_assets.csv"

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


async def load() -> None:
    """Load sample dataset into Neo4j."""
    if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
        raise EnvironmentError("Missing Neo4j connection settings")

    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    await run_queries(driver, parse_schema())

    df = pd.read_csv(DATA_PATH)
    async with driver.session(database=NEO4J_DATABASE) as session:
        for row in df.itertuples(index=False):
            partners = [p.strip() for p in str(row.partners).split(";") if p.strip()]
            cypher = (
                "MERGE (a:Asset {id: $id}) SET a.name=$name, a.city=$city "
                "MERGE (c:City {name:$city}) "
                "MERGE (a)-[:LOCATED_IN]->(c) "
                "MERGE (t:Type {name:$type}) "
                "MERGE (a)-[:HAS_TYPE]->(t) "
                "WITH a "
                "UNWIND $partners AS pname "
                "MERGE (p:Partner {name:pname}) "
                "MERGE (p)-[:CO_INVESTED]->(a)"
            )
            await session.run(
                cypher,
                {
                    "id": row.id,
                    "name": row.name,
                    "city": row.city,
                    "type": row.type,
                    "partners": partners,
                },
            )
    await driver.close()


if __name__ == "__main__":
    asyncio.run(load())
