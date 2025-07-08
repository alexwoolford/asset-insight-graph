# Asset Insight Graph

Asset Insight Graph demonstrates a small knowledge graph backed by Neo4j Aura and a minimal FastAPI service providing GraphRAG endpoints.

## Repository Layout

```text
.
├── api/                # FastAPI service
├── etl/                # Data loading scripts
├── docker/             # Dockerfile for the API
├── docs/               # Diagrams
├── tests/              # Pytest suites
```


## Quick Start
=======

1. Copy `.env.example` to `.env` and fill in the Neo4j and OpenAI credentials.
2. Install dependencies and pre-commit hooks:

```bash
make setup
```

3. Load the sample dataset to Neo4j Aura:

```bash
make load
```

4. Load the CIM Group asset dataset scraped from the web:

```bash
make load-cim
```

5. Run the API service locally:

```bash
make run
```

The health endpoint should respond with `{"status": "ok"}`:

```bash
curl http://localhost:8000/health
```

## Development

Run the test suite with:

```bash
make test
```

See `docs/arch.svg` for a high level architecture diagram.
