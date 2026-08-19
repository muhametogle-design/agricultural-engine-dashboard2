"""Authentication primitives: PBKDF2 password hashing + HS256 JWT access tokens.

Design notes:
  * Passwords use stdlib ``hashlib.pbkdf2_hmac`` (260k iterations, SHA-256) -
    NIST-acceptable, no native dependency drift (bcrypt/passlib on 3.13).
    Swap for argon2/bcrypt behind the same two functions if preferred.
  * JWTs carry ``sub`` (user id), ``tid`` (tenant id), ``role`` and ``email``.
    Every request re-validates the user row (is_active, tenant) so disabling a
    user takes effect immediately without token revocation lists.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from pydantic import BaseModel

from app.config import Settings
from app.core.errors import AppError

PBKDF2_ITERATIONS = 260_000
ALGORITHM = "HS256"


class AuthenticationError(AppError):
    status_code = 401
    code = "authentication_failed"


class AuthorizationError(AppError):
    status_code = 403
    code = "forbidden"


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return (
        f"pbkdf2_sha256${PBKDF2_ITERATIONS}$"
        f"{base64.b64encode(salt).decode()}$"
        f"{base64.b64encode(dk).decode()}"
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt_b64, hash_b64 = stored.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(dk, expected)
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

class TokenClaims(BaseModel):
    sub: UUID   # user id
    tid: UUID   # tenant id
    email: str
    role: str


def create_access_token(settings: Settings, *, user_id: UUID, tenant_id: UUID,
                        email: str, role: str) -> tuple[str, int]:
    expires_in = settings.jwt_expiry_hours * 3600
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM), expires_in


def decode_access_token(settings: Settings, token: str) -> TokenClaims:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        return TokenClaims(**payload)
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("access token expired") from exc
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise AuthenticationError("invalid access token") from exc
