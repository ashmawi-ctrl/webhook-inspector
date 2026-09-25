from app.security import is_valid_signature, sign_payload


def test_valid_signature() -> None:
    payload = b'{"event":"payment.completed"}'
    secret = "test-secret"
    signature = sign_payload(payload, secret)

    assert is_valid_signature(payload, signature, secret)


def test_invalid_signature() -> None:
    payload = b'{"event":"payment.completed"}'

    assert not is_valid_signature(payload, "wrong-signature", "test-secret")
