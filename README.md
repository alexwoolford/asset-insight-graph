# Asset Insight Graph

Asset Insight Graph demonstrates a small knowledge graph backed by Neo4j Aura and a minimal FastAPI service providing GraphRAG endpoints.

## Repository Layout

```text
.
├── api/                # FastAPI service
├── etl/                # Data loading scripts
├── docs/               # Diagrams
├── tests/              # Pytest suites
```


## 🚀 Quick Start

### 🐍 Clean Conda Environment (Recommended)

For a clean, reproducible setup using conda:

```bash
# Create and setup the CIM conda environment
make setup

# Activate the environment  
conda activate cim

# Configure credentials (copy .env.example to .env)
cp .env.example .env
# Edit .env with your Neo4j and OpenAI credentials
```

📖 **See [SETUP.md](SETUP.md) for complete setup instructions and troubleshooting.**

### 📊 Load Data and Start API

```bash
# Load CIM asset data with native geospatial Point types
make load

# Verify the knowledge graph
make verify

# Start the API service
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
Details on generating the CIM asset dataset can be found in
`docs/data_sources.md`.

## Features

This implementation includes several improvements over basic knowledge graphs:

### 🏗️ Knowledge Graph
- **Real CIM Asset Data**: 12 actual CIM Group properties (no synthetic data)
- **Geographic Hierarchy**: Asset → City → State → Region with geocoded coordinates
- **Business Intelligence**: Platform, BuildingType, and InvestmentType classifications
- **Spatial Analysis**: Distance-based queries and geographic clustering
- **🌍 Native Geospatial**: Neo4j Point types with spatial indexing (recommended loader)

### 🤖 Advanced Geospatial GraphRAG
- **Pattern-Based Query Engine**: Handles natural language questions like "assets in California" or "portfolio distribution"
- **🌍 Spatial Queries**: "nearby assets", "assets within 20km of Los Angeles", "assets in LA area"
- **Business Analytics**: "real estate assets", "commercial buildings"
- **Portfolio Analysis**: Investment type distribution, regional analysis
- **Bounding Box Queries**: Market area analysis with predefined geographic regions

### 🚀 Future Enhancements
See `docs/graph_model_enhancements.md` for a comprehensive plan to add:
- Financial data (ROI, valuations, performance metrics)
- Temporal data (acquisition dates, development timelines)
- Market data (comparables, pricing trends)
- ESG metrics (sustainability scores, green certifications)
- Risk assessment (climate risk, market volatility)

## API Usage Examples

Query the knowledge graph using natural language:

```bash
# Geographic queries
curl -X POST http://localhost:8000/qa -H 'Content-Type: application/json' -d '{"question": "assets in California"}'

# Geospatial queries
curl -X POST http://localhost:8000/qa -H 'Content-Type: application/json' -d '{"question": "assets within 20km of Los Angeles"}'
curl -X POST http://localhost:8000/qa -H 'Content-Type: application/json' -d '{"question": "assets in LA area"}'

# Portfolio analysis  
curl -X POST http://localhost:8000/qa -H 'Content-Type: application/json' -d '{"question": "portfolio distribution"}'

# Building type analysis
curl -X POST http://localhost:8000/qa -H 'Content-Type: application/json' -d '{"question": "commercial buildings"}'
```
