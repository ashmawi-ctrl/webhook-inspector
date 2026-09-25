import hashlib
import hmac


def sign_payload(payload: bytes, secret: str) -> str:
    """Return an HMAC-SHA256 hex digest for a raw webhook payload."""
    return hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


def is_valid_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Compare a supplied signature with the expected digest in constant time."""
    if not signature:
        return False
    expected = sign_payload(payload, secret)
    return hmac.compare_digest(expected, signature.strip())
