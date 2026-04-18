ROOT_DIR := $(shell pwd)
PYTHON := $(shell if [ -x "$(ROOT_DIR)/.venv/bin/python" ]; then echo "$(ROOT_DIR)/.venv/bin/python"; else echo python3; fi)

.PHONY: api-install web-install api-dev web-dev api-test demo-test

api-install:
	cd apps/api && $(PYTHON) -m pip install fastapi httpx 'uvicorn[standard]' pytest

web-install:
	cd apps/web && npm install

api-dev:
	cd apps/api && $(PYTHON) -m uvicorn app.main:app --reload --port 8000

web-dev:
	cd apps/web && npm run dev

api-test:
	cd apps/api && $(PYTHON) -m pytest

demo-test:
	cd demo-repo && python3 -m unittest discover -s tests -v && python3 checks/check_contract.py && python3 checks/check_invariants.py
