# Asset Insight Graph

Asset Insight Graph demonstrates a small knowledge graph backed by Neo4j Aura and a minimal FastAPI service providing GraphRAG endpoints.

## Repository Layout

```text
.
├── api/                # FastAPI service
│   ├── asset_queries/  # Predefined Cypher queries and schemas
│   └── ...
├── etl/                # Data loading scripts
├── workflows/          # Generated workflow diagrams (PNG)
├── docs/               # Documentation and diagram generation
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

Details on generating the CIM asset dataset can be found in
`docs/data_sources.md`.

## 🎨 User Interface

### Streamlit Web UI

For a user-friendly experience similar to ps-genai-agents, use the Streamlit interface:

**Option 1: Auto-start everything (Recommended)**
```bash
# Start both API and UI automatically
make start-all
```

**Option 2: Manual control (2 terminals)**
```bash
# Terminal 1: Start API backend
make run

# Terminal 2: Start UI frontend  
make ui-demo
```

**Option 3: Step-by-step guidance**
```bash
# Get instructions for complete setup
make demo
```

The UI provides:
- 💬 **Chat Interface**: Natural language queries with conversation history
- 🔄 **Workflow Visualization**: See which agents process your questions
- 📊 **Data Visualizations**: Automatic charts for portfolio and geographic data
- 🔍 **Cypher Details**: Expandable sections showing generated queries
- 📥 **Data Export**: Download query results as CSV files
- 🎯 **Example Questions**: Click-to-try sample queries in the sidebar

### Workflow Diagrams

To visualize the multi-agent workflow you can generate a Mermaid diagram:

```bash
python docs/generate_diagram.py
```

This creates `workflows/multi_tool_workflow.png` showing the tool selection
and summarization steps.

## Features

This implementation includes several improvements over basic knowledge graphs:

### 🏗️ Knowledge Graph
- **Real CIM Asset Data**: 12 actual CIM Group properties (no synthetic data)
- **Geographic Hierarchy**: Asset → City → State → Region with geocoded coordinates
- **Business Intelligence**: Platform, BuildingType, and InvestmentType classifications
- **Spatial Analysis**: Distance-based queries and geographic clustering
- **🌍 Native Geospatial**: Neo4j Point types with spatial indexing (recommended loader)

### 🤖 Advanced Asset Query GraphRAG
- **Pattern-Based Query Engine**: Handles natural language questions like "assets in California" or "portfolio distribution"
- **🌍 Spatial Queries**: "nearby assets", "assets within 20km of Los Angeles", "assets in LA area"
- **Business Analytics**: "real estate assets", "commercial buildings"
- **Portfolio Analysis**: Investment type distribution, regional analysis
- **Geographic Queries**: State and region-based asset searches

### 🚀 Future Enhancements
Potential areas for expansion include:
- Financial data (ROI, valuations, performance metrics)
- Temporal data (acquisition dates, development timelines)
- Market data (comparables, pricing trends)
- ESG metrics (sustainability scores, green certifications)
- Risk assessment (climate risk, market volatility)

## 🚀 Usage Examples

### Web Interface (Recommended)

The easiest way to interact with the system is through the Streamlit web UI:

```bash
# Start complete demo (API + UI)
make start-all

# Or get step-by-step instructions
make demo
```

Try these example questions in the web interface:
- "assets in California"
- "portfolio distribution" 
- "assets within 20km of Los Angeles"
- "commercial buildings"
- "how many assets"

### API Usage (Advanced)

You can also query the knowledge graph directly via API:

```bash
# Geographic queries
curl -X POST http://localhost:8000/qa -H 'Content-Type: application/json' -d '{"question": "assets in California"}'

# Geospatial queries
curl -X POST http://localhost:8000/qa -H 'Content-Type: application/json' -d '{"question": "assets within 20km of Los Angeles"}'

# Portfolio analysis  
curl -X POST http://localhost:8000/qa -H 'Content-Type: application/json' -d '{"question": "portfolio distribution"}'

# Building type analysis
curl -X POST http://localhost:8000/qa -H 'Content-Type: application/json' -d '{"question": "commercial buildings"}'
```
