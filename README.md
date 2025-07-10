# Asset Insight Graph

A sophisticated real estate portfolio analysis system using **LangGraph workflows**, Neo4j graph database, and intelligent query processing.

## 🚀 Architecture

This system uses **modern LangGraph workflow orchestration** for intelligent query processing:

### Core Components
- **LangGraph Workflows**: State-machine based query orchestration with proper routing
- **Intent Classification**: Smart categorization of user queries
- **Vector Search**: Semantic similarity using OpenAI embeddings
- **Template-Based Cypher**: Robust, validated query generation
- **Neo4j Graph Database**: High-performance graph storage with vector indexing

### Workflow Overview
```
Question → Intent Classification → Workflow Routing → Data Processing → Response Formatting
```

**Supported Query Types:**
- **Portfolio Analysis**: Asset distribution by platform, region, type
- **Geographic Search**: Location-based asset filtering with geospatial support  
- **Semantic Search**: Vector similarity using asset descriptions
- **Combined Queries**: Geographic + semantic filtering with proper vector search
- **Economic Data**: Interest rates, unemployment, market indicators

## 🛠 Setup

### Prerequisites
- Python 3.11+
- Neo4j 5.x with APOC and GDS plugins
- OpenAI API key

### Installation

1. **Clone and install dependencies:**
```bash
git clone <repository>
cd asset-insight-graph
pip install -r requirements.txt
```

2. **Configure environment variables:**
```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"  
export NEO4J_PASSWORD="your_password"
export NEO4J_DATABASE="neo4j"
export OPENAI_API_KEY="your_openai_api_key"
```

3. **Load data into Neo4j:**
```bash
# Load sample real estate portfolio data
python -m etl.cim_loader

# Load economic indicators
python -m etl.fred_loader

# Create vector embeddings
python -m etl.vector_loader
```

4. **Start the API:**
```bash
uvicorn api.main:app --reload --port 8000
```

5. **Launch Streamlit interface:**
```bash
streamlit run streamlit_app.py --server.port 8501
```

## 📊 Usage

### API Endpoints

**Ask Questions:**
```bash
curl -X POST "http://localhost:8000/qa" \
  -H "Content-Type: application/json" \
  -d '{"question": "Properties in Texas that are ESG friendly"}'
```

**Generate Workflow Diagram:**
```bash
curl "http://localhost:8000/workflow-diagram"
```

**Health Check:**
```bash
curl "http://localhost:8000/health"
```

### Example Queries

**Portfolio Analysis:**
- "Portfolio distribution by platform"
- "How many infrastructure assets"
- "Assets by region"

**Geographic Search:**
- "Assets in California"
- "Commercial buildings in Texas"
- "Assets within 100km of Los Angeles"

**Semantic Search:**
- "Properties similar to The Independent"
- "Sustainable renewable energy projects"
- "ESG friendly properties"

**Combined Queries:**
- "Properties in Texas that are ESG friendly" ✅ *Now works with proper vector search!*
- "Luxury assets in California"

## 🏗 Technical Architecture

### LangGraph Workflow System

The system uses **LangGraph StateGraph** for intelligent workflow orchestration:

```python
workflow = StateGraph(AssetGraphState)

# Workflow nodes
workflow.add_node("classify_intent", self._classify_intent_node)
workflow.add_node("portfolio_analysis", self._portfolio_analysis_node)
workflow.add_node("geographic_search", self._geographic_search_node)
workflow.add_node("semantic_search", self._semantic_search_node)
workflow.add_node("economic_data", self._economic_data_node)
workflow.add_node("format_response", self._format_response_node)

# Conditional routing based on intent
workflow.add_conditional_edges("classify_intent", self._route_by_intent, {...})
```

### Key Features

✅ **Real Vector Search**: Proper semantic similarity using embeddings
✅ **Geographic Filtering**: Combined location + semantic queries  
✅ **Workflow Orchestration**: LangGraph state machine architecture
✅ **Automatic Diagrams**: Generated workflow visualizations
✅ **Real Integration Tests**: No mocks - tests actual database behavior
✅ **Neo4j Date Serialization**: Proper handling of temporal data types

### Fixed Issues

- **Geographic+Semantic Search**: Now uses proper vector embeddings instead of broken keyword matching
- **Health Endpoint**: Returns comprehensive database status
- **Test Coverage**: Real integration tests that catch actual bugs (no mocks!)

## 🧪 Testing

**Run real integration tests:**
```bash
pytest tests/ -v
```

**Key test categories:**
- Real database connectivity tests
- Vector search functionality validation  
- Geographic filtering accuracy
- Portfolio analytics correctness
- Error handling robustness

*Note: Tests hit actual database and validate real system behavior*

## 📈 Performance & Scaling

### Database Optimizations
- Vector indexes on asset descriptions (`asset_description_vector`)
- Composite indexes for geographic queries
- Optimized Cypher templates with parameter binding

### Caching Strategy
- Cached Neo4j driver connections
- LangGraph workflow compilation caching
- Template-based query reuse

## 🔧 Development

### Project Structure
```
├── api/
│   ├── graphrag.py          # Main LangGraph implementation
│   ├── main.py              # FastAPI application  
│   └── config.py            # Database configuration
├── etl/                     # Data loading pipeline
├── tests/                   # Real integration tests
├── docs/workflows/          # Auto-generated diagrams
└── streamlit_app.py         # User interface
```

### Workflow Diagram Generation
Automatic diagram generation using LangGraph:
```bash
curl "http://localhost:8000/workflow-diagram"
# → docs/workflows/langgraph_workflow.png
```

## 🎯 Key Improvements Achieved

1. **Modern Architecture**: LangGraph workflows replace simple if/else routing
2. **Real Vector Search**: Proper semantic similarity with geographic filtering
3. **Industry Standards**: StateGraph, workflow orchestration, automatic documentation
4. **Bug-Free Testing**: Real integration tests catch actual issues
5. **Clean Codebase**: Consolidated implementation, removed legacy complexity

## 📋 Requirements

See `requirements.txt` for complete dependency list. Key packages:
- `langgraph >= 0.2.40` - Workflow orchestration
- `langsmith >= 0.1.40` - Monitoring integration  
- `neo4j >= 5.x` - Graph database driver
- `openai` - Embeddings and language models
- `fastapi` - API framework
- `streamlit` - User interface

---

**Built with LangGraph workflows for modern, reliable asset portfolio analysis.**
