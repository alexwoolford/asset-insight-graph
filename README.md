# Asset Insight Graph

Asset Insight Graph demonstrates a small knowledge graph backed by Neo4j Aura and a minimal FastAPI service providing GraphRAG endpoints.

## 📊 Data Accuracy & Verification

**All data is verifiable and sourced from official channels.** Asset information is scraped directly from CIM Group's official website and enhanced using OpenAI GPT-4 based only on real content. No speculative data is included.

📖 **See [DATA_ACCURACY.md](DATA_ACCURACY.md) for complete details on our data sourcing and verification process.**

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

### 🎯 One-Command Setup (Recommended)

For the fastest setup, use our complete setup command:

```bash
# 1. Clone and setup environment
git clone <repository-url>
cd asset-insight-graph
make setup

# 2. Configure credentials
cp .env.example .env
# Edit .env with your Neo4j credentials (required)
# Optionally add OPENAI_API_KEY for vector search

# 3. Complete setup (loads data + creates vectors if OpenAI key provided)
conda activate cim
make complete-setup

# 4. Launch the application
make start-all
```

🌐 **Open http://localhost:8501 to start querying your knowledge graph!**

### 🐍 Manual Setup (Alternative)

For step-by-step control:

```bash
# Create and setup the conda environment
make setup && conda activate cim

# Configure credentials (copy .env.example to .env)
cp .env.example .env
# Edit .env with your Neo4j and OpenAI credentials

# Load CIM asset data with native geospatial Point types
make load

# Verify the knowledge graph
make verify

# Optional: Setup vector search (requires OPENAI_API_KEY)
make vectors

# Start the API service
make run
```

### ✅ Verify Setup

The health endpoint should respond with `{"status": "ok"}`:

```bash
curl http://localhost:8000/health
```

📖 **See [SETUP.md](SETUP.md) for complete setup instructions and troubleshooting.**

### 🧠 Enable Vector Search (Optional)

For semantic similarity search capabilities, set up vector embeddings:

```bash
# 1. Set OpenAI API key in .env file
echo "OPENAI_API_KEY=your-key-here" >> .env

# 2. Generate enhanced property descriptions
cd etl && python property_descriptions.py

# 3. Create vector embeddings and load into Neo4j
python vector_loader.py

# 4. Test vector search
cd .. && curl -X POST http://localhost:8000/qa \
  -H 'Content-Type: application/json' \
  -d '{"question": "sustainable renewable energy projects"}'
```

**Note**: Vector search requires an OpenAI API key and will make API calls to generate embeddings.

## Development

Run the test suite with:

```bash
make test
```

Details on generating the CIM asset dataset can be found in
`docs/data_sources.md`.

## 🎨 User Interface

### Streamlit Web UI

For a user-friendly experience, use the Streamlit interface:

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
make ui
```

**Option 3: Get launch instructions**
```bash
# Get instructions for launching the application
make launch
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

### 🧠 Vector Similarity Search
- **Semantic Property Discovery**: "Find luxury developments with premium amenities"
- **Investment Strategy Matching**: "ESG-focused sustainable investments"
- **Market Similarity**: "Properties in tech innovation hubs"
- **Asset Comparison**: "Assets similar to Tribune Tower"
- **OpenAI Embeddings**: Rich property descriptions converted to 1536-dimensional vectors
- **Neo4j Vector Index**: Cosine similarity search for semantic matching

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

**Traditional Graph Queries:**
- "assets in California"
- "portfolio distribution" 
- "assets within 20km of Los Angeles"
- "commercial buildings"
- "how many assets"
- "commercial properties in Texas"

**Vector Similarity Search** (requires OpenAI setup):
- "sustainable renewable energy projects"
- "luxury urban developments"
- "ESG-focused investments"
- "properties similar to Tribune Tower"
- "assets with premium amenities"

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

# Vector similarity search (requires OpenAI API key)
curl -X POST http://localhost:8000/qa -H 'Content-Type: application/json' -d '{"question": "sustainable renewable energy projects"}'

curl -X POST http://localhost:8000/qa -H 'Content-Type: application/json' -d '{"question": "luxury urban developments"}'

curl -X POST http://localhost:8000/qa -H 'Content-Type: application/json' -d '{"question": "ESG-focused investments"}'
```

## 🏗️ Architecture Overview

The Asset Insight Graph demonstrates all **5 Neo4j access patterns**:

1. **Node Property Query** - Direct asset lookups by name or ID
2. **Graph Traversal Query** - Following relationships (Asset → City → State → Region)
3. **Full Text Search** - Pattern matching on asset names and descriptions  
4. **Graph Data Science** - Geospatial distance calculations and clustering
5. **Vector Search** - Semantic similarity using OpenAI embeddings

This comprehensive approach enables both precise structured queries and flexible semantic exploration of real estate investment data.

### Query Processing Flow

```
User Query → Pattern Detection → Route to:
├── Traditional Graph Query (Cypher)
├── Geospatial Query (Neo4j Point types)  
└── Vector Similarity Search (OpenAI embeddings)
```
