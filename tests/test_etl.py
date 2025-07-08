from __future__ import annotations

import os

import pytest

from api.config import Settings, get_driver
from etl.load_sample_dataset import load


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("NEO4J_PASSWORD"), reason="Neo4j credentials not provided"
)
async def test_etl_load() -> None:
    await load()
    driver = get_driver()
    settings = Settings()
    async with driver.session(database=settings.neo4j_db) as session:
        result = await session.run("MATCH (a:Asset) RETURN count(a) AS c")
        count = (await result.single())[0]
    assert count > 0


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("NEO4J_PASSWORD"), reason="Neo4j credentials not provided"
)
async def test_cim_etl_load() -> None:
    from etl.load_cim_dataset import load as load_cim

    await load_cim()
    driver = get_driver()
    settings = Settings()
    async with driver.session(database=settings.neo4j_db) as session:
        result = await session.run("MATCH (a:Asset) RETURN count(a) AS c")
        count = (await result.single())[0]
    assert count > 0
