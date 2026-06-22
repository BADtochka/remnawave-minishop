PYTHON ?= python
NPM ?= npm

MYPY_PATHS := \
	backend/db \
	backend/bot/infra \
	backend/bot/payment_providers \
	backend/bot/services \
	backend/bot/handlers \
	backend/bot/app/web/admin_api_impl \
	backend/bot/app/web/webapp \
	backend/bot/app/web/http_contracts.py \
	backend/bot/app/web/route_contracts.py \
	backend/bot/app/web/openapi.py

.PHONY: test lint types front check cov

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

types:
	$(PYTHON) -m mypy $(MYPY_PATHS)

front:
	$(NPM) --prefix frontend run check
	$(NPM) --prefix frontend run build

check: test lint types front

cov:
	$(PYTHON) -m pytest --cov=backend --cov-report=term-missing
