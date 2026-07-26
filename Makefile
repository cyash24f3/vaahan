.PHONY: install check test run

install:
	python -m pip install -e '.[dev]'

check:
	ruff check src tests
	ruff format --check src tests
	mypy
	pytest

test:
	pytest

run:
	uvicorn vaahan.app:app --host 0.0.0.0 --port 7860

