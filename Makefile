# Python 3.12 or 3.13. The first make command creates .venv and installs requirements-dev.txt.
PYTHON ?= $(shell command -v python3.13 || command -v python3.12 || command -v python3)
VENV ?= .venv
PY := $(VENV)/bin/python
export PYTHONPATH := src

.PHONY: setup demo test eval lint api stack stack-demo down sample

setup: $(VENV)/.installed

$(VENV)/.installed: requirements.txt requirements-dev.txt
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install -q -r requirements-dev.txt
	touch $@

demo: setup  ## run 9 loads, 4 with defects, 5 findings, SQLite audit log, no Docker
	$(PY) -m dqf.demo

test: setup
	$(PY) -m pytest --cov=dqf --cov-report=term-missing -q

eval: setup  ## detection and false-positive rates per defect type (about 5 to 10 minutes)
	$(PY) -m dqf.evaluate --trials 200 --seed 7

lint: setup
	$(PY) -m ruff check . && $(PY) -m ruff format --check .

api: setup  ## health and alert endpoints over the demo audit log
	DATABASE_URL=sqlite:///demo_audit.db $(PY) -m uvicorn dqf.api:app --port 8010

sample: setup  ## rebuild data/sample from the public NYC TLC file (downloads 50 MB)
	$(PY) scripts/make_sample.py

stack:  ## Postgres + Airflow + API in Docker
	docker compose up -d --build --wait

stack-demo: stack  ## trigger the DAG for clean and defective loads, then read the API
	./scripts/stack_demo.sh

down:
	docker compose down -v
