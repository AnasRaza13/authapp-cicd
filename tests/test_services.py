"""Unit tests for the BUSINESS layer: registration, login and tenant rules."""
import pytest

from app.business.services import AuthError, AuthService, slugify
from app.data.models import Tenant

PW = "password123"


def register(db, company="Acme Corp", username="alice", email=None, password=PW, confirm=None):
    email = email or f"{username}@example.com"
    confirm = password if confirm is None else confirm
    return AuthService(db).register(company, username, email, password, confirm)


# ------------------------------------------------------------------- slugify
@pytest.mark.parametrize(
    "name, expected",
    [
        ("Acme Corp", "acme-corp"),
        ("  ACME   corp ", "acme-corp"),
        ("acme-corp", "acme-corp"),
        ("Cafe 42", "cafe-42"),
        ("!!!", ""),
    ],
)
def test_slugify(name, expected):
    assert slugify(name) == expected


# ---------------------------------------------------------------- validation
@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"company": "A"}, "Company name"),
        ({"company": "!!!"}, "Company name"),
        ({"company": "x" * 51}, "Company name"),
        ({"username": "ab"}, "Username"),
        ({"username": "bad name"}, "Username"),
        ({"email": "not-an-email"}, "valid email"),
        ({"password": "short1", "confirm": "short1"}, "at least 8"),
        ({"password": "a" * 73, "confirm": "a" * 73}, "at most 72"),
        ({"confirm": "different123"}, "do not match"),
    ],
)
def test_registration_rejects_invalid_input(db, overrides, message):
    with pytest.raises(AuthError, match=message):
        register(db, **overrides)


def test_failed_registration_does_not_leave_an_empty_company_behind(db):
    with pytest.raises(AuthError):
        register(db, company="Orphan Co", username="ab")
    assert db.query(Tenant).count() == 0


# ------------------------------------------------------------ roles & tenants
def test_first_user_of_a_company_is_admin_and_later_users_are_members(db):
    first = register(db, username="alice")
    second = register(db, company="acme-corp", username="bob")
    assert first.role == "admin"
    assert second.role == "member"
    assert first.tenant_id == second.tenant_id  # "acme-corp" joined "Acme Corp"


def test_same_username_and_email_are_allowed_in_different_companies(db):
    a = register(db, company="Acme Corp", username="alice", email="alice@example.com")
    g = register(db, company="Globex", username="alice", email="alice@example.com")
    assert a.id != g.id
    assert a.tenant_id != g.tenant_id


def test_duplicate_username_in_one_company_is_rejected_case_insensitively(db):
    register(db, username="alice")
    with pytest.raises(AuthError, match="already taken"):
        register(db, username="ALICE", email="other@example.com")


def test_duplicate_email_in_one_company_is_rejected(db):
    register(db, username="alice", email="alice@example.com")
    with pytest.raises(AuthError, match="already exists"):
        register(db, username="dave", email="Alice@Example.com")


# --------------------------------------------------------------------- login
def test_login_succeeds_with_any_spelling_of_the_company(db):
    register(db)
    assert AuthService(db).authenticate("  ACME   corp ", "alice", PW).username == "alice"


@pytest.mark.parametrize(
    "company, username, password",
    [
        ("Acme Corp", "alice", "wrongpass1"),  # wrong password
        ("Acme Corp", "nobody", PW),           # unknown user
        ("No Such Co", "alice", PW),           # unknown company
    ],
)
def test_all_login_failures_give_the_same_message(db, company, username, password):
    register(db)
    with pytest.raises(AuthError, match="Invalid company, username or password"):
        AuthService(db).authenticate(company, username, password)


def test_a_password_only_opens_the_account_in_its_own_company(db):
    register(db, company="Acme Corp", username="alice", password="password123")
    register(db, company="Globex", username="alice", password="globexpass1")
    service = AuthService(db)
    assert service.authenticate("Globex", "alice", "globexpass1").tenant.slug == "globex"
    with pytest.raises(AuthError):
        service.authenticate("Globex", "alice", "password123")
    with pytest.raises(AuthError):
        service.authenticate("Acme Corp", "alice", "globexpass1")


# ------------------------------------------------------------------ isolation
def test_get_user_only_returns_a_user_of_the_given_tenant(db):
    acme_alice = register(db, company="Acme Corp", username="alice")
    globex_alice = register(db, company="Globex", username="alice")
    service = AuthService(db)
    assert service.get_user(acme_alice.id, acme_alice.tenant_id) is not None
    assert service.get_user(globex_alice.id, acme_alice.tenant_id) is None


def test_list_members_never_includes_other_companies(db):
    alice = register(db, company="Acme Corp", username="alice")
    register(db, company="Acme Corp", username="bob")
    register(db, company="Globex", username="carol")
    names = sorted(u.username for u in AuthService(db).list_members(alice))
    assert names == ["alice", "bob"]
