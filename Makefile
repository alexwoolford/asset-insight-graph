# Asset Insight Graph - Conda Environment Makefile
# Uses the 'cim' conda environment for clean, reproducible setup

.PHONY: help setup install clean load verify test run cleanup

# Default conda environment name
CONDA_ENV ?= cim

help: ## Show this help message
	@echo "Asset Insight Graph - Conda Environment Commands"
	@echo "================================================"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Create and setup the conda environment from scratch
	conda create -n $(CONDA_ENV) python=3.11 -y
	conda run -n $(CONDA_ENV) pip install -r requirements.txt
	@echo "✅ CIM conda environment setup complete!"
	@echo "📋 Activate with: conda activate $(CONDA_ENV)"

install: ## Install dependencies in existing conda environment
	conda run -n $(CONDA_ENV) pip install -r requirements.txt

clean: ## Remove the conda environment completely
	conda env remove -n $(CONDA_ENV) -y

load-cim: ## Load CIM asset data with native geospatial Point types
	conda run -n $(CONDA_ENV) python etl/cim_loader.py

verify: ## Verify the knowledge graph was loaded correctly
	conda run -n $(CONDA_ENV) python etl/verify_knowledge_graph.py

test: ## Run the test suite
	conda run -n $(CONDA_ENV) --no-capture-output python -m pytest tests/ -v

run: ## Start the FastAPI server
	conda run -n $(CONDA_ENV) --no-capture-output uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

cleanup: ## Clean up Neo4j database for fresh start
	conda run -n $(CONDA_ENV) python etl/database_cleanup.py

# Development targets
dev-deps: ## Install development dependencies
	conda run -n $(CONDA_ENV) pip install pytest pytest-asyncio black isort ruff

format: ## Format code with black and isort
	conda run -n $(CONDA_ENV) black .
	conda run -n $(CONDA_ENV) isort .

lint: ## Lint code with ruff
	conda run -n $(CONDA_ENV) ruff check .

check: ## Run all code quality checks
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) test

ui: ## Start the Streamlit UI interface
	conda run -n $(CONDA_ENV) --no-capture-output streamlit run streamlit_app.py

vectors: ## Generate basic AI descriptions and vector embeddings (requires OPENAI_API_KEY)
	@echo "🧠 Setting up basic vector similarity search..."
	@echo "💡 Note: Uses generic AI-generated descriptions"
	@echo "💡 Use 'make enhanced-setup' for web-scraped descriptions instead"
	@echo "📝 Step 1: Generating basic property descriptions..."
	conda run -n $(CONDA_ENV) python etl/property_descriptions.py
	@echo "🚀 Step 2: Creating vector embeddings and loading into Neo4j..."
	conda run -n $(CONDA_ENV) python etl/vector_loader.py
	@echo "✅ Vector search setup complete!"
	@echo "🔍 Test with: make test-vectors"

descriptions: ## Generate property descriptions for vector search
	@echo "🏢 Generating property descriptions for vector search..."
	@echo "📝 Creating comprehensive property descriptions..."
	conda run -n $(CONDA_ENV) python etl/property_descriptions.py
	@echo "✅ Property descriptions generated!"
	@echo "📁 Saved to: etl/cim_assets_descriptions.jsonl"

descriptions-setup: ## Generate property descriptions and vector embeddings (RECOMMENDED)
	@echo "🧠 Setting up vector similarity search with property descriptions..."
	@echo "✅ Using comprehensive AI-generated property descriptions"
	@echo "📝 Step 1: Generating property descriptions..."
	$(MAKE) descriptions
	@echo "🚀 Step 2: Creating vector embeddings and loading into Neo4j..."
	conda run -n $(CONDA_ENV) python etl/vector_loader.py
	@echo "✅ Vector search setup complete!"
	@echo "🔍 Test with: make test-vectors"

test-vectors: ## Test vector similarity search capabilities
	@echo "🔍 Testing vector similarity search..."
	@echo "💡 Trying: 'sustainable renewable energy projects'"
	curl -s -X POST http://localhost:8000/qa -H 'Content-Type: application/json' -d '{"question": "sustainable renewable energy projects"}' | jq -r '.answer'
	@echo "💡 Trying: 'luxury urban developments'"
	curl -s -X POST http://localhost:8000/qa -H 'Content-Type: application/json' -d '{"question": "luxury urban developments"}' | jq -r '.answer'

complete-setup: ## Complete setup from scratch with enhanced data (database + vectors)
	@echo "🚀 Complete Asset Insight Graph Setup"
	@echo "====================================="
	@echo "✅ Using verified CIM Group website data"
	@echo "📊 Step 1: Loading CIM asset data..."
	$(MAKE) load-cim
	@echo "🔍 Step 2: Verifying knowledge graph..."
	$(MAKE) verify
	@echo "🧠 Step 3: Setting up vector search (if OPENAI_API_KEY is set)..."
	@if [ -n "$$OPENAI_API_KEY" ]; then \
		$(MAKE) descriptions-setup; \
	else \
		echo "⚠️  OPENAI_API_KEY not set - skipping vector search setup"; \
		echo "💡 Set OPENAI_API_KEY in .env to enable semantic similarity search"; \
	fi
	@echo "✅ Complete setup finished!"
	@echo "🚀 Start the application with: make start-all"

complete-setup-basic: ## Complete setup with basic synthetic data (for testing only)
	@echo "🚀 Complete Asset Insight Graph Setup (Basic)"
	@echo "=============================================="
	@echo "⚠️  WARNING: Uses basic AI-generated descriptions"
	@echo "📊 Step 1: Loading CIM asset data..."
	$(MAKE) load-cim
	@echo "🔍 Step 2: Verifying knowledge graph..."
	$(MAKE) verify
	@echo "🧠 Step 3: Setting up basic vector search (if OPENAI_API_KEY is set)..."
	@if [ -n "$$OPENAI_API_KEY" ]; then \
		$(MAKE) vectors; \
	else \
		echo "⚠️  OPENAI_API_KEY not set - skipping vector search setup"; \
		echo "💡 Set OPENAI_API_KEY in .env to enable semantic similarity search"; \
	fi
	@echo "✅ Complete basic setup finished!"
	@echo "🚀 Start the application with: make start-all"

launch: ## Launch the complete application (alternative to demo)
	@echo "🚀 Launching Asset Insight Graph..."
	@echo "📡 FastAPI: http://localhost:8000"
	@echo "🎨 Streamlit: http://localhost:8501"
	@echo "📊 Knowledge graph with 12 CIM Group assets"
	@echo "🧠 Vector search: $(shell [ -n "$$OPENAI_API_KEY" ] && echo "✅ Enabled" || echo "❌ Disabled (set OPENAI_API_KEY)")"
	@echo ""
	@echo "💡 Open two terminals and run:"
	@echo "   Terminal 1: make run      # API backend"
	@echo "   Terminal 2: make ui       # Streamlit interface"
	@echo ""
	@echo "Or use: make start-all  # Starts both in background"

start-all: ## Start both API and UI in background
	@echo "🚀 Starting Asset Insight Graph (API + UI)..."
	@echo "📡 FastAPI: http://localhost:8000"
	@echo "🎨 Streamlit: http://localhost:8501"
	nohup conda run -n $(CONDA_ENV) uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > api.log 2>&1 &
	sleep 3
	nohup conda run -n $(CONDA_ENV) streamlit run streamlit_app.py --server.port 8501 > ui.log 2>&1 &
	@echo "✅ Both services started in background"
	@echo "📋 Check logs: tail -f api.log ui.log"
	@echo "🛑 Stop with: make stop-all"

stop-all: ## Stop all background services
	@echo "🛑 Stopping all services..."
	-pkill -f "uvicorn api.main:app"
	-pkill -f "streamlit run streamlit_app.py"
	@echo "✅ All services stopped"

gds-analysis: ## Run Graph Data Science community detection analysis
	@echo "🧠 Running GDS community detection and geographic analysis..."
	@echo "💡 Discover hidden patterns in asset clustering and geographic distribution"
	conda run -n $(CONDA_ENV) python etl/gds_analysis.py
	@echo "✅ GDS analysis complete!" 

load-fred: ## Load FRED economic data with timeseries chain structure (requires FRED_API_KEY)
	@echo "🏦 Loading FRED data with timeseries chain structure..."
	@echo "📊 Creating HEAD/TAIL links and NEXT chain relationships"
	@echo "💡 Requires FRED_API_KEY - get free key at: https://fred.stlouisfed.org/docs/api/api_key.html"
	conda run -n $(CONDA_ENV) python etl/fred_loader.py
	@echo "✅ FRED timeseries chain structure complete!"



wipe-database: ## Completely wipe the database (all nodes, relationships, constraints, indexes)
	@echo "🧹 WARNING: This will completely wipe the database!"
	conda run -n $(CONDA_ENV) python etl/database_reset.py --force



fresh-start: ## Complete fresh start: wipe database + load CIM + load FRED chains
	@echo "🚀 Complete Fresh Start with Timeseries Chains"
	@echo "=============================================="
	@echo "⚠️  WARNING: This will wipe the entire database!"
	@echo "📊 Steps: 1) Wipe database 2) Load CIM assets 3) Load FRED chains"
	@echo ""
	@if [ -n "$$FRED_API_KEY" ]; then \
		$(MAKE) wipe-database; \
		$(MAKE) load-cim; \
		$(MAKE) load-fred; \
		$(MAKE) verify; \
		echo "✅ Fresh start complete with timeseries chains!"; \
	else \
		echo "❌ FRED_API_KEY not set in .env file"; \
		echo "💡 Get a free API key at: https://fred.stlouisfed.org/docs/api/api_key.html"; \
		echo "📝 Add to .env: FRED_API_KEY=your_api_key_here"; \
	fi