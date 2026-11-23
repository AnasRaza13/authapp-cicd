"""DATA LAYER - database engine, session factory, declarative base and schema check."""
import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

# users.db is created in the project root (next to requirements.txt).
# Set the AUTH_DB_PATH environment variable to use a different file. On the production
# server it points outside the release folders so a deployment never touches the data.
DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "users.db"
DB_PATH = Path(os.getenv("AUTH_DB_PATH", str(DEFAULT_DB_PATH)))
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    # SQLite connections are single-thread by default; FastAPI uses a thread pool
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yields one DB session per request and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ping(db) -> bool:
    """True if the database answers a trivial query (used by the /health endpoint)."""
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def check_schema(bind) -> None:
    """Stop early, with a clear message, if the database file was created by the old
    single-tenant version of the app (its users table has no tenant_id column)."""
    inspector = inspect(bind)
    if inspector.has_table("users"):
        columns = {col["name"] for col in inspector.get_columns("users")}
        if "tenant_id" not in columns:
            raise RuntimeError(
                "The database file '%s' was created by the old single-tenant version "
                "(its users table has no tenant_id column). Stop the server, delete that "
                "file, and start again - a new multi-tenant database is created automatically."
                % bind.url.database
            )
