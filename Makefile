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