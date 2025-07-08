from __future__ import annotations

import os
from functools import lru_cache

from neo4j import AsyncGraphDatabase
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    neo4j_uri: str | None = os.getenv("NEO4J_URI")
    neo4j_user: str | None = os.getenv("NEO4J_USERNAME")
    neo4j_pwd: str | None = os.getenv("NEO4J_PASSWORD")
    neo4j_db: str = os.getenv("NEO4J_DATABASE", "neo4j")


@lru_cache
def get_driver() -> AsyncGraphDatabase:
    """Return a cached Neo4j driver instance."""
    s = Settings()
    return AsyncGraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_pwd))
