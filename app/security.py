"""HMAC verification of the `X-Signature-256` header sent by submit.py."""
import hashlib
import hmac
import os

from fastapi import HTTPException, status


def sign(body: bytes, secret: bytes) -> str:
    return "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()


def verify_signature(body: bytes, header: str | None) -> None:
    """Reject a bad signature with 401.

    A missing header is allowed (the browser frontend cannot hold the secret)
    unless REQUIRE_SIGNATURE is set. A header that is sent must always be valid.
    """
    secret = os.getenv("SIGNING_KEY")
    required = os.getenv("REQUIRE_SIGNATURE", "").lower() in ("1", "true", "yes")
    if header is None:
        if required:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing X-Signature-256 header")
        return
    if not secret:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "SIGNING_KEY is not configured")
    if not hmac.compare_digest(header, sign(body, secret.encode("utf-8"))):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signature")
