from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from .config import Settings
from .geospatial_tools import get_cypher_statements_dictionary, get_tool_schemas

# These imports are optional and loaded inside the workflow function


@lru_cache
def get_multi_agent_workflow():
    """Return a cached multi-agent workflow instance."""
    settings = Settings()
    from langchain_neo4j import Neo4jGraph
    from langchain_openai import ChatOpenAI
    from ps_genai_agents.components.text2cypher import get_text2cypher_schema
    from ps_genai_agents.retrievers.cypher_examples.yaml import (
        YAMLCypherExampleRetriever,
    )
    from ps_genai_agents.workflows.multi_agent import create_multi_tool_workflow

    graph = Neo4jGraph(
        url=settings.neo4j_uri,
        username=settings.neo4j_user,
        password=settings.neo4j_pwd,
        database=settings.neo4j_db,
        enhanced_schema=True,
        driver_config={"liveness_check_timeout": 0},
    )

    yaml_path = Path(__file__).resolve().parents[1] / "example_queries.yml"
    retriever = YAMLCypherExampleRetriever(cypher_query_yaml_file_path=str(yaml_path))

    llm_model = os.getenv("OPENAI_MODEL", "gpt-4o")
    llm = ChatOpenAI(
        model=llm_model, temperature=0.0, openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    tool_schemas = get_tool_schemas() + [get_text2cypher_schema()]
    cypher_dict = get_cypher_statements_dictionary()

    return create_multi_tool_workflow(
        llm=llm,
        graph=graph,
        tool_schemas=tool_schemas,
        predefined_cypher_dict=cypher_dict,
        cypher_example_retriever=retriever,
        llm_cypher_validation=False,
    )
