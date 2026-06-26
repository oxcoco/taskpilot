VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

.PHONY: venv install run test clean frontend

# Create virtual environment
venv:
	python3 -m venv $(VENV)

# Install dependencies into the venv
install: venv
	$(PIP) install -r requirements.txt

# Run the interactive UI
run: install
	PYTHONPATH=$(CURDIR):$(CURDIR)/.. $(PYTHON) -m taskpilot.app.run_ui

# Execute the full pytest test suite
test: install
	PYTHONPATH=$(CURDIR):$(CURDIR)/.. $(VENV)/bin/pytest -q

# Clean the virtual environment and database artifacts
frontend: install
	PYTHONPATH=$(CURDIR):$(CURDIR)/.. $(PYTHON) -m taskpilot.app.api & \
	cd frontend && npm install && npm run dev
