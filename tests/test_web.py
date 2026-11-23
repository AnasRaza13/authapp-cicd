"""Tests through HTTP: the presentation layer talking to the layers below it."""
import base64
import json
from pathlib import Path

from itsdangerous import TimestampSigner

from app.data.models import User
from app.main import app
from app.version import APP_VERSION
from fastapi.testclient import TestClient

PW = "password123"
ROOT = Path(__file__).resolve().parents[1]


def register(client, company, username, email, password=PW):
    return client.post("/register", data={
        "company": company, "username": username, "email": email,
        "password": password, "confirm_password": password,
    })


def login(client, company, username, password=PW):
    return client.post("/login", data={
        "company": company, "username": username, "password": password,
    }, follow_redirects=False)


# ------------------------------------------------------------- pages & release
def test_login_and_register_pages_render_with_a_company_field(client):
    assert 'name="company"' in client.get("/").text
    assert 'name="company"' in client.get("/?mode=register").text


def test_footer_shows_the_application_version(client):
    # This is the visible change the CI/CD demo makes by editing the VERSION file
    assert f"Version {APP_VERSION}" in client.get("/").text


def test_health_reports_status_version_and_build(client):
    response = client.get("/health")
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["version"] == (ROOT / "VERSION").read_text().strip()
    assert "build" in body


# --------------------------------------------------------------------- flows
def test_register_login_welcome_and_logout(client):
    assert "Account created" in register(client, "Acme Corp", "alice", "alice@example.com").text
    assert login(client, "Acme Corp", "alice").status_code == 303

    page = client.get("/").text
    assert "Welcome, alice" in page and "Acme Corp" in page and "admin" in page

    client.post("/logout")
    assert "Welcome, alice" not in client.get("/").text


def test_wrong_password_gets_401_and_a_generic_message(client):
    register(client, "Acme Corp", "alice", "alice@example.com")
    response = client.post("/login", data={"company": "Acme Corp", "username": "alice", "password": "nope-nope"})
    assert response.status_code == 401
    assert "Invalid company, username or password" in response.text


def test_each_company_only_sees_its_own_members(client):
    register(client, "Acme Corp", "alice", "alice@example.com")
    register(client, "Acme Corp", "bob", "bob@example.com")
    register(client, "Globex", "carol", "carol@example.com")

    acme = TestClient(app)
    login(acme, "Acme Corp", "alice")
    page = acme.get("/").text
    assert "bob" in page and "carol" not in page

    globex = TestClient(app)
    login(globex, "Globex", "carol")
    page = globex.get("/").text
    assert "carol" in page and "bob" not in page


# ----------------------------------------------------------- forged sessions
def _session_cookie(payload):
    raw = base64.b64encode(json.dumps(payload).encode("utf-8"))
    return TimestampSigner("test-secret-key").sign(raw).decode("utf-8")


def test_a_session_pairing_a_user_with_the_wrong_tenant_is_rejected(client, db):
    register(client, "Acme Corp", "alice", "alice@example.com")
    register(client, "Globex", "alice", "alice@example.com")
    acme_alice = db.query(User).filter(User.tenant.has(slug="acme-corp")).one()
    globex_alice = db.query(User).filter(User.tenant.has(slug="globex")).one()

    good = TestClient(app)
    good.cookies.set("session", _session_cookie({"user_id": acme_alice.id, "tenant_id": acme_alice.tenant_id}))
    assert "Welcome, alice" in good.get("/").text  # control: a matching pair is accepted

    forged = TestClient(app)
    forged.cookies.set("session", _session_cookie({"user_id": globex_alice.id, "tenant_id": acme_alice.tenant_id}))
    assert "Welcome" not in forged.get("/").text
