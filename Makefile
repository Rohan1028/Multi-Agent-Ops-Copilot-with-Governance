PYTHON=python
PIP=$(PYTHON) -m pip
POETRY?=poetry

.PHONY: setup format lint test run index bench clean

setup:
	$(PIP) install -r requirements.txt

format:
	$(PYTHON) -m black app providers scripts
	$(PYTHON) -m isort app providers scripts

lint:
	$(PYTHON) -m flake8 app providers scripts
	$(PYTHON) -m mypy app providers scripts

test:
	$(PYTHON) -m pytest

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

index:
	$(PYTHON) -m app.main index

bench:
	$(PYTHON) scripts/run_benchmarks.py

clean:
	rm -rf __pycache__ */__pycache__
	rm -rf .mypy_cache .pytest_cache
	rm -rf app/runtime reports *.sqlite
	rm -rf app/data/*.pkl
	rm -rf sandbox_repo
