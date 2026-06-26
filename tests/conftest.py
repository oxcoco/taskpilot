import os, sys
import pytest

# Ensure the project root is on PYTHONPATH for imports
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from taskpilot.database.db import create_tables

@pytest.fixture(autouse=True)
def clean_db():
    """Create fresh tables and wipe any existing data before each test."""
    # Drop and recreate tables to ensure a clean state
    # Simple approach: delete the sqlite file if it exists
    db_path = os.path.join(PROJECT_ROOT, "sqlite.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    create_tables()
    yield
    # No teardown needed
