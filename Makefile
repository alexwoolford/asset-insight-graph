setup:
poetry install
pre-commit install

load:
poetry run python etl/load_sample_dataset.py

run:
poetry run uvicorn api.main:app --host 0.0.0.0 --port 8000

test:
poetry run pytest -q