PYTHON ?= python

.PHONY: run
run:
	$(PYTHON) -m src.app

.PHONY: env
environment:
	pip install -r requirements.txt

.PHONY: uv env
environment:
	uv pip install -r requirements.txt
