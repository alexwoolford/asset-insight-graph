# Asset Insight Graph

**Intelligent Real Estate Portfolio Analysis using Neo4j Knowledge Graphs with FRED Economic Intelligence**

A sophisticated knowledge graph system that combines CIM Group's real estate portfolio data with Federal Reserve Economic Data (FRED) to enable advanced business intelligence queries and analysis.

> **🎯 Production Ready**: Repository has been cleaned of temporary files and migration scripts. All components are optimized and ready for deployment.

## 🏗️ **System Architecture**

### **Knowledge Graph Components**
- **CIM Asset Portfolio**: 12 real estate assets across multiple platforms (Real Estate, Infrastructure, Credit)
- **FRED Economic Data**: Federal Reserve timeseries data with optimized chain structure
- **Geographic Hierarchy**: Country → State → City → Asset relationships
- **Vector Search**: Semantic similarity search capabilities

### **Timeseries Chain Structure**
```
MetricType → HEAD → MetricValue (first) 
MetricType → TAIL → MetricValue (latest)
MetricValue → NEXT → MetricValue → NEXT → ... (chronological chain)
```

**Benefits:**
- ⚡ Fast access to first/last values via HEAD/TAIL
- 🔗 Efficient chronological traversal via NEXT relationships  
- 📊 Optimal for regular monthly/quarterly data reading
- 🎯 Perfect chain integrity with no gaps

## 🚀 **Quick Start**

### **Prerequisites**
- Python 3.11+
- Neo4j Database
- Conda environment

### **Setup**
```bash
# 1. Setup conda environment
make setup

# 2. Configure environment variables (.env file)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DB=neo4j
OPENAI_API_KEY=your_openai_key  # Optional for vector search
FRED_API_KEY=your_fred_key      # Required for economic data
```

### **Complete Fresh Start**
```bash
# One command to build everything
make fresh-start
```

This will:
1. 🧹 Wipe the database completely
2. 📊 Load CIM asset data  
3. 📈 Load FRED economic data with timeseries chains
4. ✅ Verify the knowledge graph

## 📊 **Data Loading Commands**

### **Individual Data Sources**
```bash
# Load CIM real estate portfolio
make load-cim

# Load FRED economic data with timeseries chains
make load-fred

# Verify data integrity
make verify
```

### **Database Management**
```bash
# Complete database wipe (removes everything)
make wipe-database

# Cleanup for fresh start
make cleanup
```

## 🔍 **Business Intelligence Capabilities**

### **Current Economic Indicators**
```bash
# Query: "Current interest rates"
# Returns: Latest rates via TAIL relationships
30-Year Mortgage Rate: 6.67% (as of 2025-07-03)
Federal Funds Rate: 4.33% (as of 2025-06-01)
```

### **Unemployment Analysis**
```bash
# Query: "Unemployment by state"  
# Returns: Current unemployment rates where we have assets
Georgia: 3.3% (1 asset)
Texas: 4.0% (2 assets)  
California: 4.9% (4 assets)
```

### **Interest Rate Trends**
```bash
# Query: "Interest rate trends"
# Returns: HEAD vs TAIL comparison showing long-term trends
Federal Funds Rate: 0.8% → 4.33% (↑3.53% over period)
```

## 🎯 **Query Examples**

### **Portfolio Intelligence**
- "Portfolio distribution by region"
- "How many infrastructure assets"
- "Real estate assets"

### **Geographic Analysis**
- "Assets within 100km of Los Angeles"
- "Assets in California"
- "Nearby assets"

### **ESG & Sustainability**
- "Properties in Texas that are ESG friendly"
- "Sustainable renewable energy projects"
- "Properties similar to The Independent"

### **Asset Classification**
- "Mixed use properties in California"
- "Commercial buildings in Texas"
- "Infrastructure assets"

## 🛠️ **Development Commands**

### **Enhanced Setup**
```bash
# Complete setup with vector search
make complete-setup

# Basic setup (no vector search)
make complete-setup-basic
```

### **Vector Search (Optional)**
```bash
# Generate property descriptions
make descriptions

# Create vector embeddings
make vectors

# Test vector search
make test-vectors
```

### **Graph Analysis**
```bash
# Run Graph Data Science analysis
make gds-analysis
```

## 🌐 **Running the Application**

### **Start Services**
```bash
# Start API and UI together
make start-all

# Or start individually:
make run    # API server (localhost:8000)
make ui     # Streamlit UI (localhost:8501)
```

### **Stop Services**
```bash
make stop-all
```

## 📈 **FRED Economic Data**

### **Data Coverage**
- **18 Economic Metrics** with timeseries chains
- **12,255 Data Points** across 2+ years
- **National Metrics**: Interest rates, GDP, housing, inflation
- **State Metrics**: Unemployment, population for CA, TX, NY, IL, GA

### **Chain Structure Benefits**
- **HEAD**: Instant access to first data point
- **TAIL**: Instant access to latest data point  
- **NEXT**: Chronological traversal of complete timeseries
- **Perfect Integrity**: No gaps or broken chains

### **API Key Setup**
Get a free FRED API key at: https://fred.stlouisfed.org/docs/api/api_key.html

Add to `.env`:
```bash
FRED_API_KEY=your_api_key_here
```

## 🎨 **User Interface**

### **Streamlit Dashboard**
- 📊 Interactive query interface
- 📈 Economic data visualization  
- 🔍 Real-time graph exploration
- 📋 Sample business intelligence queries

### **FastAPI Backend**
- 🚀 High-performance async API
- 🧠 GraphRAG query processing
- 🔗 Neo4j knowledge graph integration
- 📡 RESTful endpoints

## 📂 **Project Structure**

```
asset-insight-graph/
├── api/                          # FastAPI backend
│   ├── graphrag.py              # Main GraphRAG query engine
│   ├── main.py                  # FastAPI application
│   └── config.py                # Database configuration
├── etl/                         # Data loading and processing
│   ├── cim_loader.py           # CIM asset data loader
│   ├── fred_loader.py          # FRED timeseries chain loader
│   ├── database_reset.py       # Database cleanup
│   ├── verify_knowledge_graph.py # Data verification
│   ├── property_descriptions.py # AI descriptions
│   └── vector_loader.py        # Vector embeddings
├── streamlit_app.py            # Streamlit UI
├── Makefile                    # Standardized commands
└── requirements.txt            # Python dependencies
```

## 🎯 **Key Features**

### **✅ Implemented**
- 🏗️ Complete knowledge graph with CIM assets
- 📈 FRED economic data with optimized timeseries chains  
- 🔍 Advanced GraphRAG query system
- 🌐 Interactive Streamlit dashboard
- 🚀 High-performance FastAPI backend
- 🧠 Vector similarity search (optional)
- 📊 Business intelligence capabilities

### **🎯 Query Capabilities**
- Geographic asset analysis
- Economic trend analysis
- Portfolio risk assessment  
- Interest rate sensitivity
- Unemployment correlation
- Real-time economic indicators

## 🔧 **Development & Testing**

### **Code Quality**
```bash
make format  # Format with black/isort
make lint    # Lint with ruff  
make check   # Run all quality checks
make test    # Run test suite
```

### **Health Checks**
```bash
# API health
curl http://localhost:8000/health

# Test business intelligence
curl -X POST http://localhost:8000/qa \
  -H 'Content-Type: application/json' \
  -d '{"question": "Current interest rates"}'
```

## 📋 **Requirements**

### **Core Dependencies**
- `neo4j>=5.14.0` - Graph database driver
- `fastapi>=0.104.0` - API framework  
- `streamlit>=1.28.0` - UI framework
- `aiohttp>=3.9.0` - Async HTTP for FRED API
- `openai>=1.3.0` - Vector embeddings (optional)

### **Development Tools**
- `pytest` - Testing framework
- `black` - Code formatting
- `ruff` - Fast linting
- `isort` - Import sorting

## 🎉 **Success Metrics**

### **Data Quality**
- ✅ **12,255 FRED data points** properly chained
- ✅ **22 MetricType nodes** with perfect HEAD/TAIL structure
- ✅ **12,237 NEXT relationships** for seamless traversal
- ✅ **Zero chain integrity issues**

### **Performance**
- ⚡ **Instant access** to latest economic indicators via TAIL
- 🔗 **Efficient traversal** of monthly timeseries via NEXT chains
- 📊 **Optimized queries** for business intelligence analysis

---

**Built with Neo4j Knowledge Graphs • FRED Economic Data • FastAPI • Streamlit**
