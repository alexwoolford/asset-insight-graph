from neo4j import AsyncGraphDatabase, AsyncDriver

async def get_driver(uri: str, user: str, password: str) -> AsyncDriver:
    """Create an asynchronous Neo4j driver."""
    return AsyncGraphDatabase.driver(uri, auth=(user, password))
