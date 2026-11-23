"""Unit tests for the DATA layer: the tenant-scoped repository."""
import pytest

from app.data.repository import DuplicateError, TenantRepository, UserRepository


def make_tenant(db, name, slug):
    tenant = TenantRepository(db).add(name, slug)
    db.commit()
    return tenant


def test_scoped_repository_cannot_see_other_tenants(db):
    acme = make_tenant(db, "Acme Corp", "acme-corp")
    globex = make_tenant(db, "Globex", "globex")
    UserRepository(db, acme.id).create("alice", "alice@example.com", "hash", "admin")
    carol = UserRepository(db, globex.id).create("carol", "carol@example.com", "hash")

    acme_repo = UserRepository(db, acme.id)
    assert acme_repo.get_by_username("carol") is None
    assert acme_repo.get_by_email("carol@example.com") is None
    assert acme_repo.get_by_id(carol.id) is None
    assert [u.username for u in acme_repo.list_all()] == ["alice"]
    assert acme_repo.count() == 1


def test_username_is_unique_per_tenant_not_globally(db):
    acme = make_tenant(db, "Acme Corp", "acme-corp")
    globex = make_tenant(db, "Globex", "globex")
    UserRepository(db, acme.id).create("alice", "a@example.com", "hash")
    UserRepository(db, globex.id).create("alice", "a@example.com", "hash")  # allowed
    with pytest.raises(DuplicateError):
        UserRepository(db, acme.id).create("alice", "other@example.com", "hash")


def test_company_slug_must_be_unique(db):
    make_tenant(db, "Acme Corp", "acme-corp")
    with pytest.raises(DuplicateError):
        TenantRepository(db).add("ACME CORP", "acme-corp")
