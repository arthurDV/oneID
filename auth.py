"""
JWT auth — zero dependencies (stdlib only).

A JWT is just 3 parts separated by dots:
  header.payload.signature

- header   = {"alg": "HS256", "typ": "JWT"}  (always the same)
- payload  = {"identity_id": "xxx", "iat": 123, "exp": 456}  (the data)
- signature = HMAC-SHA256(header.payload, secret)  (proves it's legit)

One token = one identity. The agent stores it, that's all it needs.
"""

import json
import hmac
import hashlib
import base64
import time
from config import JWT_SECRET

# --- helpers ---

def _b64url_encode(data: bytes) -> str:
    """Base64url encode (no padding) — JWT standard."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    """Base64url decode (re-add padding)."""
    s += "=" * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s)


# --- create token ---

def create_token(identity_id: str, expires_in: int = 86400 * 365) -> str:
    """
    Create a JWT token for one identity.
    Default expiry = 1 year.
    """
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())

    now = int(time.time())
    payload_data = {
        "identity_id": identity_id,
        "iat": now,
        "exp": now + expires_in,
    }
    payload = _b64url_encode(json.dumps(payload_data).encode())

    signature_input = f"{header}.{payload}".encode()
    sig = hmac.new(JWT_SECRET.encode(), signature_input, hashlib.sha256).digest()
    signature = _b64url_encode(sig)

    return f"{header}.{payload}.{signature}"


# --- verify token ---

def verify_token(token: str) -> dict | None:
    """
    Verify a JWT token. Returns the payload dict if valid, None if not.
    Checks: signature + expiration.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature_b64 = parts

        signature_input = f"{header_b64}.{payload_b64}".encode()
        expected_sig = hmac.new(JWT_SECRET.encode(), signature_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(signature_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(_b64url_decode(payload_b64))

        if payload.get("exp", 0) < int(time.time()):
            return None

        return payload

    except Exception:
        return None
