"""BUSINESS LAYER - password hashing (passlib + bcrypt)."""
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Used to burn the same CPU time when a username does not exist, so response
# timing does not reveal which usernames are registered.
_DUMMY_HASH = _pwd_context.hash("dummy-password-for-timing")


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    if hashed_password is None:
        _pwd_context.verify(plain_password, _DUMMY_HASH)
        return False
    return _pwd_context.verify(plain_password, hashed_password)
