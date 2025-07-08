.PHONY: setup load run run-dev test

setup:
	@echo "Running setup"

load:
	@echo "Running load"

run:
        @echo "Running run"

run-dev:
	poetry run uvicorn api.main:app --reload

test:
	@echo "Running test"
