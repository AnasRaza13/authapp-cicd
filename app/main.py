"""Application entry point - wires the three layers together."""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.data import models  # noqa: F401  (import so the tables are registered)
from app.data.database import Base, check_schema, engine
from app.presentation.routes import router
from app.version import APP_VERSION

# Refuse to run against a database made by the old single-tenant version (clear message)
check_schema(engine)
# Create the SQLite file and the "tenants" and "users" tables on first run
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AuthApp - multi-tenant", version=APP_VERSION)

# Signed-cookie sessions. On the server SECRET_KEY comes from /etc/authapp.env.
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-only-secret-change-me"),
    same_site="lax",
    https_only=False,  # the demo server speaks plain HTTP; set True once HTTPS is in place
)

STATIC_DIR = Path(__file__).resolve().parent / "presentation" / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(router)
