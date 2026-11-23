"""DATA LAYER - ORM models (table definitions).

Multi-tenancy model: ONE database, ONE schema. Every company is a row in `tenants`,
and every user row carries the `tenant_id` of the company it belongs to.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    # Normalised name used for lookups: "Acme Corp" and "acme-corp" -> "acme-corp"
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="tenant")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        # Unique PER TENANT, so two companies can both have an "alice"
        UniqueConstraint("tenant_id", "username", name="uq_users_tenant_username"),
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), index=True, nullable=False
    )
    username: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    # Only the bcrypt hash is stored - never the plain-text password
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(10), default="member", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    tenant: Mapped["Tenant"] = relationship(back_populates="users")
