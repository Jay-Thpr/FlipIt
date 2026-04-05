PYTHON ?= python3
VENV ?= .venv
VENV_FETCH ?= .venv-fetch
ACTIVATE = . $(VENV)/bin/activate
ACTIVATE_FETCH = . $(VENV_FETCH)/bin/activate

.PHONY: install test test-verbose compile check run run-agents run-fetch-agents ci verify-browser

install:
	$(PYTHON) -m venv $(VENV)
	$(ACTIVATE) && python -m pip install --upgrade pip
	$(ACTIVATE) && python -m pip install -r requirements.txt

test:
	$(ACTIVATE) && python -m pytest -q

test-verbose:
	$(ACTIVATE) && python -m pytest -ra

compile:
	$(ACTIVATE) && python -m compileall backend tests

check: test compile

run:
	$(ACTIVATE) && ./start.sh

run-agents:
	$(ACTIVATE) && python -m backend.run_agents

run-fetch-agents:
	$(ACTIVATE_FETCH) && PYTHONPATH=$$PWD python -m backend.run_fetch_agents

ci: check

verify-browser:
	$(ACTIVATE) && python -m backend.browser_use_runtime_audit
