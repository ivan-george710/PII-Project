from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()
# Verify unknown accounts too, so account existence does not skip password hashing.
DUMMY_HASH = password_hasher.hash("unused-random-account-placeholder")


def hash_password(password: str) -> str:
    if not 12 <= len(password) <= 128:
        raise ValueError("Password must contain 12 to 128 characters")
    return password_hasher.hash(password)


def verify_password(password: str, hashed: str | None) -> bool:
    try:
        valid = password_hasher.verify(password, hashed or DUMMY_HASH)
    except (ValueError, TypeError):
        return False
    return bool(hashed) and valid
