PY ?= python3
export PYTHONPATH := src

.PHONY: demo test eval lint api stack stack-demo down sample

demo:  ## run 9 loads, 4 with defects, 5 findings, SQLite audit log, no Docker
	$(PY) -m dqf.demo

test:
	$(PY) -m pytest --cov=dqf --cov-report=term-missing -q

eval:  ## detection and false-positive rates per defect type (about 5 to 10 minutes)
	$(PY) -m dqf.evaluate --trials 200 --seed 7

lint:
	ruff check . && ruff format --check .

api:  ## health and alert endpoints over the demo audit log
	DATABASE_URL=sqlite:///demo_audit.db $(PY) -m uvicorn dqf.api:app --port 8010

sample:  ## rebuild data/sample from the public NYC TLC file (downloads 50 MB)
	$(PY) scripts/make_sample.py

stack:  ## Postgres + Airflow + API in Docker
	docker compose up -d --build --wait

stack-demo: stack  ## trigger the DAG for clean and defective loads, then read the API
	./scripts/stack_demo.sh

down:
	docker compose down -v
