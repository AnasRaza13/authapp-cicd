"""BUSINESS LAYER - tenant, registration and login rules.

This layer knows nothing about HTTP, HTML or SQL. It validates input, resolves which
tenant (company) a request is about, applies the rules, hashes/verifies passwords and
talks to the data layer through the repositories.
"""
import re

from sqlalchemy.orm import Session

from app.business.security import hash_password, verify_password
from app.data.models import User
from app.data.repository import DuplicateError, TenantRepository, UserRepository

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LEN = 8
MAX_PASSWORD_BYTES = 72  # bcrypt only uses the first 72 bytes
MIN_COMPANY_LEN, MAX_COMPANY_LEN = 2, 50


class AuthError(Exception):
    """Raised for any expected, user-facing problem (bad input, wrong password...)."""


def slugify(company: str) -> str:
    """'Acme Corp', 'acme-corp' and '  ACME   corp ' all become 'acme-corp'."""
    return re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-")


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.tenants = TenantRepository(db)

    # ---------------------------------------------------------------- register
    def register(self, company: str, username: str, email: str,
                 password: str, confirm_password: str) -> User:
        company = " ".join(company.split())  # trim and collapse spaces
        username, email = username.strip(), email.strip()
        slug = slugify(company)

        if not (MIN_COMPANY_LEN <= len(company) <= MAX_COMPANY_LEN) or not slug:
            raise AuthError(
                f"Company name must be {MIN_COMPANY_LEN}-{MAX_COMPANY_LEN} characters "
                "and include at least one letter or number (A-Z, 0-9)."
            )
        if not USERNAME_RE.match(username):
            raise AuthError("Username must be 3-30 characters: letters, numbers or underscore.")
        if not EMAIL_RE.match(email) or len(email) > 255:
            raise AuthError("Please enter a valid email address.")
        if len(password) < MIN_PASSWORD_LEN:
            raise AuthError(f"Password must be at least {MIN_PASSWORD_LEN} characters long.")
        if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise AuthError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes long.")
        if password != confirm_password:
            raise AuthError("Passwords do not match.")

        try:
            tenant = self.tenants.get_by_slug(slug)
            if tenant is not None:
                # Joining an existing company: duplicates are checked INSIDE that tenant only
                users = UserRepository(self.db, tenant.id)
                if users.get_by_username(username):
                    raise AuthError("That username is already taken in this company.")
                if users.get_by_email(email):
                    raise AuthError("An account with that email already exists in this company.")
            else:
                # New company: it is created together with its first user
                tenant = self.tenants.add(company, slug)
                users = UserRepository(self.db, tenant.id)

            # The first person in a company becomes its admin, everyone after is a member
            role = "admin" if users.count() == 0 else "member"
            return users.create(username, email, hash_password(password), role)
        except DuplicateError:
            raise AuthError("That company or username was just taken. Please try again.")

    # ------------------------------------------------------------------- login
    def authenticate(self, company: str, username: str, password: str) -> User:
        slug = slugify(company.strip())
        tenant = self.tenants.get_by_slug(slug) if slug else None
        user = UserRepository(self.db, tenant.id).get_by_username(username.strip()) if tenant else None

        stored_hash = user.hashed_password if user else None
        # verify_password always does the hashing work, even for unknown users/companies
        if not verify_password(password, stored_hash) or user is None:
            # Same message for "no such company", "no such user" and "wrong password"
            raise AuthError("Invalid company, username or password.")
        return user

    # ---------------------------------------------------------------- sessions
    def get_user(self, user_id: int, tenant_id: int) -> User | None:
        """A user is only returned if the id belongs to that tenant. A session that says
        'user 7 of tenant 2' but where user 7 lives in tenant 1 gets nothing back."""
        return UserRepository(self.db, tenant_id).get_by_id(user_id)

    def list_members(self, user: User) -> list[User]:
        """Everyone in the same company as `user` - never anyone from another tenant."""
        return UserRepository(self.db, user.tenant_id).list_all()
