# Python stack preset for AI Cockpit.

PROJECT_FORMAT_CHECK = $(PYTHON) -m ruff format --check .
PROJECT_TEST = $(PYTHON) -m pytest
PROJECT_LINT = $(PYTHON) -m ruff check .
