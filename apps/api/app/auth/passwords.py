from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()
# Verify unknown accounts too, so account existence does not skip password hashing.
DUMMY_HASH = password_hasher.hash("unused-random-account-placeholder")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed: str | None) -> bool:
    try:
        valid = password_hasher.verify(password, hashed or DUMMY_HASH)
    except (ValueError, TypeError):
        return False
    return bool(hashed) and valid
