PYTHON ?= python3
VENV ?= .venv
FETCH_PYTHON ?= python3.12
FETCH_VENV ?= .venv-fetch
ACTIVATE = . $(VENV)/bin/activate
FETCH_ACTIVATE = . $(FETCH_VENV)/bin/activate

.PHONY: install venv-fetch test test-verbose compile check run run-agents run-fetch-agents run-fetch-agent ci verify-browser

install:
	$(PYTHON) -m venv $(VENV)
	$(ACTIVATE) && python -m pip install --upgrade pip
	$(ACTIVATE) && python -m pip install -r requirements.txt

venv-fetch:
	$(FETCH_PYTHON) -m venv $(FETCH_VENV)
	$(FETCH_ACTIVATE) && python -m pip install --upgrade pip
	$(FETCH_ACTIVATE) && python -m pip install -r requirements.txt

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
	$(FETCH_ACTIVATE) && PYTHONPATH=$$PWD python -m backend.run_fetch_agents

# One uAgent at a time (single inspector URL in the terminal). Stop any `make run-fetch-agents` first.
# Usage: set -a && source .env && set +a && make run-fetch-agent AGENT=vision_agent
run-fetch-agent:
	@if [ -z "$(AGENT)" ]; then echo 'Usage: set -a && source .env && set +a && make run-fetch-agent AGENT=vision_agent'; exit 1; fi
	$(FETCH_ACTIVATE) && PYTHONPATH=$$PWD python -m backend.fetch_agents.launch $(AGENT)

ci: check

verify-browser:
	$(ACTIVATE) && python -m backend.browser_use_runtime_audit
