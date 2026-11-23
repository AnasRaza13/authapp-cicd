"""DATA LAYER - all database queries live here, so no other layer writes SQL/ORM calls.

UserRepository is TENANT-SCOPED: it is built for exactly one tenant and every query it
runs is automatically filtered by that tenant_id. Code in the upper layers cannot
forget the filter, because there is no way to ask this class for another tenant's rows.
"""
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.data.models import Tenant, User


class DuplicateError(Exception):
    """A unique constraint was violated (for example two people registering at once)."""


class TenantRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_slug(self, slug: str) -> Tenant | None:
        return self.db.scalars(select(Tenant).where(Tenant.slug == slug)).first()

    def add(self, name: str, slug: str) -> Tenant:
        """Stage a new tenant. It is committed together with its first user."""
        tenant = Tenant(name=name, slug=slug)
        self.db.add(tenant)
        try:
            self.db.flush()  # assigns tenant.id without committing yet
        except IntegrityError:
            self.db.rollback()
            raise DuplicateError("tenant already exists")
        return tenant


class UserRepository:
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    def _scoped(self):
        """Base query: users of THIS tenant only."""
        return select(User).where(User.tenant_id == self.tenant_id)

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.scalars(self._scoped().where(User.id == user_id)).first()

    def get_by_username(self, username: str) -> User | None:
        stmt = self._scoped().where(func.lower(User.username) == username.lower())
        return self.db.scalars(stmt).first()

    def get_by_email(self, email: str) -> User | None:
        stmt = self._scoped().where(func.lower(User.email) == email.lower())
        return self.db.scalars(stmt).first()

    def list_all(self) -> list[User]:
        return list(self.db.scalars(self._scoped().order_by(User.created_at, User.id)))

    def count(self) -> int:
        stmt = select(func.count()).select_from(User).where(User.tenant_id == self.tenant_id)
        return self.db.scalar(stmt) or 0

    def create(self, username: str, email: str, hashed_password: str, role: str = "member") -> User:
        user = User(
            tenant_id=self.tenant_id,
            username=username,
            email=email.lower(),
            hashed_password=hashed_password,
            role=role,
        )
        self.db.add(user)
        try:
            self.db.commit()  # also commits a tenant staged by TenantRepository.add()
        except IntegrityError:
            self.db.rollback()
            raise DuplicateError("user already exists in this tenant")
        self.db.refresh(user)
        return user
