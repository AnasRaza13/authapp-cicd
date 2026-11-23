"""Shared test setup.

The environment variables are set BEFORE the app is imported, so every test runs against
a throw-away SQLite file in a temp folder - never against a real users.db.
"""
import os
import tempfile
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="authapp-tests-")
os.environ["AUTH_DB_PATH"] = str(Path(_TMP) / "test.db")
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.data.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database():
    """Every test starts with empty tenants and users tables."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)
