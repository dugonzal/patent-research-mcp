.PHONY: install test test-all test-cov lint format format-check typecheck clean build

install:
	pip install -e ".[dev]"

test:
	python -m pytest -v --tb=short -m "not e2e"

test-all:
	python -m pytest -v --tb=short

test-cov:
	python -m pytest --cov=patent_research_mcp --cov-report=term-missing --cov-report=xml -m "not e2e"

lint:
	ruff check src/

format:
	ruff format src/

format-check:
	ruff format --check src/

typecheck:
	mypy src/

clean:
	rm -rf build/ dist/ .eggs/ *.egg-info/
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name .pytest_cache -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name .ruff_cache -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name .mypy_cache -type d -exec rm -rf {} + 2>/dev/null || true

build: clean
	python -m build
