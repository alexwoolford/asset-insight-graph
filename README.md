# asset-insight-graph

Asset Insight Graph is a Neo4j‑powered knowledge graph that links real‑estate assets, locations, stakeholders, tenants and timeline events, all sourced from public data. It supports interactive exploration, graph analytics and Retrieval‑Augmented Generation (GraphRAG) to uncover hidden risks and opportunities across diversified portfolios.

## Key Features

 - Unified Knowledge Model – Properties, partners, tenants, lenders and events stored as first‑class nodes and relationships.
 - Graph Analytics – Centrality, community detection and path‑finding via the Neo4j Graph Data Science (GDS) library.
 - GraphRAG API – Natural‑language Q&A and summarization endpoints that ground LLM answers in graph results.
 - Extensible Schema – Easily add infrastructure, credit, ESG and external market data.
 - Zero Confidential Data – Entirely built from public sources (press releases, municipal records, open datasets).

## Repository Layout

```
.
├── docker/                 # Dockerfiles & docker‑compose.yml
├── etl/                    # Ingestion scripts (Python)
├── notebooks/              # Jupyter prototypes & data exploration
├── neo4j/                  # Cypher seeds, constraints, indexes
├── api/                    # FastAPI service exposing GraphRAG endpoints
├── docs/                   # Diagrams & supplementary markdown
└── tests/                  # Pytest suites
```

## Quick Start (Local Dev)
Docker is optional and may not work in restricted environments.
```
# 1. Clone
git clone https://github.com/your-org/asset-insight-graph.git
cd asset-insight-graph

# 2. Start Neo4j + API (Docker optional)
docker compose up -d     # default creds: neo4j / neo4j (may fail in restricted env)
# or run the API locally (when Docker isn't available):
poetry run uvicorn api.main:app --reload
# or via Makefile
make run-dev

# 3. Ingest sample data
pip install -r etl/requirements.txt
python etl/load_sample_dataset.py --neo4j-bolt bolt://localhost:7687

# 4. Verify graph
cypher-shell -u neo4j -p neo4j \
'MATCH (a:Asset) RETURN a.name LIMIT 10;'
```

## Example Cypher Queries
```
// 1. Find tenants shared by at least two assets
MATCH (t:Tenant)-->(a:Asset)
WITH t, collect(a) AS assets WHERE size(assets) > 1
RETURN t.name AS tenant, size(assets) AS assetCount, assets;

// 2. Most central partners (betweenness)
CALL gds.betweenness.stream('partnerGraph')
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).name AS partner, score
ORDER BY score DESC LIMIT 10;

// 3. Potential risk path (tenant -> asset -> lender)
MATCH path = (t:Tenant {name:$name})-->(a:Asset)-->(l:Lender)
RETURN path LIMIT 20;
```

## GraphRAG Endpoint (FastAPI)
```
curl -X POST http://localhost:8000/qa \
     -H "Content-Type: application/json" \
     -d '{"question": "Which partners co-invest in more than three assets?"}'
```
### Example response:
```
{
  "answer": "Partner X and Partner Y each appear in 5 assets, concentrated in Chicago and Dallas respectively.",
  "cypher": "...",
  "data": [...]
}
```

## Roadmap
 - Data Coverage – Add infrastructure and credit assets.
 - Geo‑Spatial Layer – Point‑in‑polygon queries, proximity edges.
 - Dashboards – Grafana/Metabase panels fed by Cypher.
 - LLM Fine‑Tuning – Portfolio‑specific retrieval templates.

## Contributing
1.	Fork the repo, create a feature branch, open a PR.
2.	Run pre-commit install to enable linting hooks.
3.	Ensure all tests pass with pytest -q.
