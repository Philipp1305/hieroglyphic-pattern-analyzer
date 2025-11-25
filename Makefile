PYTHON ?= python

.PHONY: run
run:
	$(PYTHON) -m src.app

.PHONY: env
env:
	pip install -r requirements.txt

.PHONY: uv-env
uv-env:
	uv venv .venv
	uv pip install -r requirements.txt

.PHONY: clean
clean:
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	find . -type d -name '.mypy_cache' -prune -exec rm -rf {} +
	find . -name '.DS_Store' -exec rm -rf {} +
