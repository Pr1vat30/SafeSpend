"""Unit tests of token creation and revocation (RNF_SE_1, RF_AUT_3). No database needed."""

import time

from app.service.profile import security


def test_token_roundtrip_and_unique_ids():
    first, expires_in = security.create_access_token(42)
    second, _ = security.create_access_token(42)

    claims = security.decode_access_token(first)
    assert claims is not None and claims.id_user == 42
    assert expires_in == 3600
    assert claims.jti != security.decode_access_token(second).jti


def test_tampered_or_garbage_token_is_rejected():
    token, _ = security.create_access_token(1)
    assert security.decode_access_token(token[:-2] + "xx") is None
    assert security.decode_access_token("non-un-token") is None


def test_revoked_token_is_rejected_and_others_are_not():
    revoked, _ = security.create_access_token(7)
    other, _ = security.create_access_token(7)
    claims = security.decode_access_token(revoked)

    security.revoked_tokens.revoke(claims.jti, claims.expires_at)

    assert security.decode_access_token(revoked) is None
    assert security.decode_access_token(other) is not None


def test_revocation_list_forgets_expired_tokens():
    revocations = security.RevokedTokens()
    revocations.revoke("scaduto", time.time() - 1)
    revocations.revoke("valido", time.time() + 60)  # adding purges the expired entries

    assert not revocations.is_revoked("scaduto")
    assert revocations.is_revoked("valido")
