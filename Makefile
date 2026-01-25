PYTHON ?= python
PRETTIER ?= npx prettier

.PHONY: run
run:
	$(PYTHON) -m src.app

.PHONY: format format-python format-frontend lint lint-fix
format: format-python format-frontend

format-python:
	ruff format .

format-frontend:
	$(PRETTIER) --write "src/app/templates/**/*.html" "!src/app/templates/components/navbar.html" "src/app/static/js/**/*.js"
lint:
	ruff check .
lint-fix:
	ruff check . --fix

.PHONY: env uv-env
env:
	pip install -r requirements.txt
uv-env:
	uv venv .venv
	uv pip install -r requirements.txt

.PHONY: clean
clean:
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	find . -type d -name '.mypy_cache' -prune -exec rm -rf {} +
	find . -name '.DS_Store' -exec rm -rf {} +
	find . -name '.ruff_cache' -exec rm -rf {} +
