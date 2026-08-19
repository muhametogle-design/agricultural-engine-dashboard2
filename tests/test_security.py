"""Unit tests for the cryptographic primitives."""
from __future__ import annotations

import uuid

import pytest

from app.config import Settings
from app.core.security import (
    AuthenticationError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    stored = hash_password("camel-tractor-river")
    assert stored.startswith("pbkdf2_sha256$")
    assert verify_password("camel-tractor-river", stored)
    assert not verify_password("camel-tractor-ocean", stored)
    # salted: two hashes of the same password differ, both verify
    other = hash_password("camel-tractor-river")
    assert other != stored and verify_password("camel-tractor-river", other)


def test_verify_password_malformed_stored_value():
    assert not verify_password("whatever", "not-a-hash")
    assert not verify_password("whatever", "bcrypt$1$a$b")


def test_access_token_roundtrip(settings):
    uid, tid = uuid.uuid4(), uuid.uuid4()
    token, expires = create_access_token(settings, user_id=uid, tenant_id=tid,
                                         email="a@b.so", role="analyst")
    claims = decode_access_token(settings, token)
    assert claims.sub == uid and claims.tid == tid and claims.role == "analyst"
    assert expires == settings.jwt_expiry_hours * 3600


def test_expired_token_rejected():
    settings = Settings(jwt_expiry_hours=-1)  # expires in the past
    token, _ = create_access_token(settings, user_id=uuid.uuid4(),
                                   tenant_id=uuid.uuid4(), email="a@b.so", role="admin")
    with pytest.raises(AuthenticationError, match="expired"):
        decode_access_token(settings, token)


def test_tampered_or_wrong_secret_rejected(settings):
    token, _ = create_access_token(settings, user_id=uuid.uuid4(),
                                   tenant_id=uuid.uuid4(), email="a@b.so", role="admin")
    with pytest.raises(AuthenticationError):
        decode_access_token(Settings(jwt_secret="different-secret"), token)
    with pytest.raises(AuthenticationError):
        decode_access_token(settings, token + "tampered")
