# Asset Insight Graph - Clean Setup Guide

This guide provides instructions for setting up the Asset Insight Graph project with a clean, reproducible conda environment.

## 🚀 Quick Start (Conda Environment)

### Prerequisites
- [Anaconda](https://www.anaconda.com/products/distribution) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- Neo4j Aura account and database
- OpenAI API key (optional, for future LLM features)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd asset-insight-graph
```

### 2. Environment Setup

Choose one of the following setup methods:

#### Option A: Automated Setup (Recommended)

```bash
# Create and setup the CIM conda environment automatically
make setup

# Activate the environment
conda activate cim
```

#### Option B: Manual Setup

```bash
# Create conda environment
conda create -n cim python=3.11 -y

# Activate environment
conda activate cim

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file with your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your Neo4j and OpenAI credentials:

```env
# Neo4j Aura Configuration
NEO4J_URI=neo4j+s://your-database-id.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DB=neo4j

# OpenAI Configuration (optional)
OPENAI_API_KEY=your-openai-key
```

### 4. Load the Knowledge Graph

```bash
# Clean any existing data (optional)
make cleanup

# Load CIM asset data with native geospatial Point types
make load

# Verify the knowledge graph
make verify
```

### 5. Start the API Server

```bash
# Start the FastAPI server
make run
```

The API will be available at `http://localhost:8000`

## 🧪 Testing

```bash
# Run the test suite
make test

# Run development quality checks
make check
```

## 📊 API Usage Examples

Once the server is running, test the geospatial GraphRAG capabilities:

```bash
# Geographic queries
curl -X POST http://localhost:8000/qa \
  -H 'Content-Type: application/json' \
  -d '{"question": "assets in California"}'

# Enhanced geospatial queries
curl -X POST http://localhost:8000/qa \
  -H 'Content-Type: application/json' \
  -d '{"question": "assets within 20km of Los Angeles"}'

curl -X POST http://localhost:8000/qa \
  -H 'Content-Type: application/json' \
  -d '{"question": "assets in LA area"}'

# Portfolio analysis
curl -X POST http://localhost:8000/qa \
  -H 'Content-Type: application/json' \
  -d '{"question": "portfolio distribution"}'
```

## 🛠️ Development Commands

The `Makefile` provides clean, conda-based commands:

```bash
# Environment management
make setup      # Create fresh environment
make install    # Install/update dependencies
make clean      # Remove environment

# Data management
make load       # Load asset data
make verify     # Verify knowledge graph
make cleanup    # Clean database

# Development
make test       # Run tests
make run        # Start API server
make dev-deps   # Install dev dependencies
make format     # Format code
make lint       # Lint code
make check      # Run all quality checks

# Help
make help       # Show all commands
```

## 📦 Dependencies

The project uses a clean `requirements.txt` with pinned versions for reproducibility:

### Production Dependencies
- **Neo4j**: Database connectivity with native geospatial support
- **FastAPI + Uvicorn**: Modern web framework and ASGI server
- **LangChain + OpenAI**: AI/LLM integration for advanced queries
- **Pandas + Httpx**: Data processing and HTTP client
- **Pydantic**: Configuration and data validation

### Development Dependencies (Optional)
- **Pytest**: Testing framework
- **Black + isort**: Code formatting
- **Ruff**: Fast Python linter

## 🌍 Geospatial Features

This setup includes advanced geospatial capabilities:

- **Native Neo4j Point Types**: Optimal performance and built-in spatial functions
- **Spatial Indexing**: Fast geographic queries with native spatial indexes
- **Distance Calculations**: Built-in `point.distance()` for proximity analysis
- **Bounding Box Queries**: Market area analysis with predefined regions
- **Geographic Clustering**: Asset proximity analysis and clustering

## 🔄 Clean Setup

This project uses a streamlined conda-based approach:

```bash
# Simple setup process
make setup
conda activate cim
```

## 🆘 Troubleshooting

### Environment Issues
```bash
# Reset environment completely
make clean
make setup
```

### Database Connection Issues
- Verify Neo4j Aura credentials in `.env`
- Check network connectivity to Neo4j Aura
- Ensure database is running and accessible

### Geospatial Query Issues
- The system now uses native Neo4j Point types
- All spatial queries use `point.distance()` for optimal performance
- Bounding box queries support predefined market areas

## 🏗️ Project Structure

```
asset-insight-graph/
├── api/                    # FastAPI application
│   ├── main.py            # API entry point
│   ├── graphrag.py        # Enhanced geospatial GraphRAG
│   └── config.py          # Configuration
├── etl/                   # Data loading and processing
│   ├── cim_loader.py            # Geospatial Point type loader
│   ├── schema.cypher            # Neo4j schema with spatial indexes
│   ├── cim_assets.jsonl          # Real CIM Group asset data
│   └── verify_knowledge_graph.py # Verification script
├── requirements.txt       # Production dependencies
├── Makefile              # Automation commands
└── SETUP.md              # This file
```

This clean setup provides a robust, reproducible environment for the Asset Insight Graph with advanced geospatial capabilities! 