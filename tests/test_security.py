from app.business.security import hash_password, verify_password


def test_hash_is_bcrypt_and_not_plain_text():
    hashed = hash_password("password123")
    assert hashed.startswith("$2")
    assert "password123" not in hashed


def test_correct_password_verifies():
    assert verify_password("password123", hash_password("password123")) is True


def test_wrong_password_is_rejected():
    assert verify_password("wrong-password", hash_password("password123")) is False


def test_same_password_gets_a_different_hash_each_time():
    assert hash_password("password123") != hash_password("password123")


def test_verifying_against_no_stored_hash_is_false():
    # Used for unknown users: it must still return False (after doing the same work)
    assert verify_password("anything", None) is False
