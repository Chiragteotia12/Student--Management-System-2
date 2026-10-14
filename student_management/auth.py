"""Local account authentication using salted PBKDF2 password hashes."""
import hashlib
import hmac
import os
from .logger import get_logger

ITERATIONS = 310_000
LOGGER = get_logger(__name__)


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    """Return hex-encoded salt and PBKDF2 hash for a password."""
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, digest_hex: str) -> bool:
    """Verify a password using constant-time digest comparison."""
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, AttributeError):
        LOGGER.warning("Password verification failed due to malformed hash data")
        return False


def validate_username(username: str) -> str:
    """Normalize a username and reject empty or overly long values."""
    value = username.strip()
    if not 3 <= len(value) <= 40:
        raise ValueError("Username must be between 3 and 40 characters.")
    if any(character.isspace() for character in value):
        raise ValueError("Username cannot contain spaces.")
    return value
