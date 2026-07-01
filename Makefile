VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: help venv format lint test clean self-lint

help:
	@echo "Available targets:"
	@echo "  venv      - Create virtualenv and install dev dependencies"
	@echo "  format    - Fix code formatting with black"
	@echo "  lint      - Check code formatting with black"
	@echo "  test      - Run pytest tests"
	@echo "  self-lint - Lint the fixture with skillsaw + this plugin"
	@echo "  clean     - Remove Python cache files and virtualenv"

$(VENV)/bin/activate: pyproject.toml
	test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install -e '.[dev]'
	touch $(VENV)/bin/activate

venv: $(VENV)/bin/activate

format: $(VENV)/bin/activate
	$(VENV)/bin/black src/ tests/

lint: $(VENV)/bin/activate
	$(VENV)/bin/black --check src/ tests/

test: $(VENV)/bin/activate
	$(VENV)/bin/pytest tests/ -v --cov=src/skillsaw_typos --cov-report=term

self-lint: $(VENV)/bin/activate
	$(VENV)/bin/skillsaw plugins
	$(VENV)/bin/skillsaw lint tests/fixture

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage coverage.xml htmlcov $(VENV)
