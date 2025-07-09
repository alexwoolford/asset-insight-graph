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

load: ## Load CIM asset data with native geospatial Point types
	conda run -n $(CONDA_ENV) python etl/cim_loader.py

verify: ## Verify the knowledge graph was loaded correctly
	conda run -n $(CONDA_ENV) python etl/verify_knowledge_graph.py

test: ## Run the test suite
	conda run -n $(CONDA_ENV) --no-capture-output python -m pytest tests/ -v

run: ## Start the FastAPI server
	conda run -n $(CONDA_ENV) --no-capture-output uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

cleanup: ## Clean up Neo4j database for fresh start
	conda run -n $(CONDA_ENV) python etl/cleanup_database.py

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

ui-demo: ## Start Streamlit UI with helpful info
	@echo "🚀 Starting Asset Insight Graph UI..."
	@echo "📊 Connect to your Neo4j database to see live data"
	@echo "💡 Example questions are provided in the sidebar"
	@echo "🌐 UI will open in your browser at http://localhost:8501"
	@echo "⚠️  Remember to start the API with: make run"
	conda run -n $(CONDA_ENV) --no-capture-output streamlit run streamlit_app.py

demo: ## Start both API and UI for complete demo experience
	@echo "🚀 Starting complete Asset Insight Graph demo..."
	@echo "📡 Starting FastAPI backend on http://localhost:8000"
	@echo "🎨 Starting Streamlit UI on http://localhost:8501"
	@echo "📊 Connect to your Neo4j database to see live data"
	@echo ""
	@echo "💡 Open two terminals and run:"
	@echo "   Terminal 1: make run      # API backend"
	@echo "   Terminal 2: make ui       # Streamlit UI"
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