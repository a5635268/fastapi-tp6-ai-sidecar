"""
双 Token、JWT 防重放与客户端上下文绑定单元测试
"""
from datetime import timedelta
import pytest

from app.core.exceptions import AuthException
from app.core.response import ApiException
from app.core.redis import RedisUtil
from app.core.security import (
    consume_refresh_token,
    create_access_token,
    create_token_pair,
    decode_token,
    revoke_user_tokens,
    validate_token,
)


@pytest.mark.asyncio
async def test_token_pair_has_required_claims_and_validates(redis_mock):
    pair = create_token_pair(42, "KOS-Test-Agent")
    access_payload = decode_token(pair["access_token"])
    refresh_payload = decode_token(pair["refresh_token"])

    for payload, token_type in ((access_payload, "access"), (refresh_payload, "refresh")):
        assert payload["sub"] == "42"
        assert payload["token_type"] == token_type
        assert payload["sid"]
        assert payload["jti"]
        assert payload["issued_at_ms"]
        assert payload["client_fingerprint"]

    assert access_payload["sid"] == refresh_payload["sid"]
    validated = await validate_token(pair["access_token"], "access", "KOS-Test-Agent")
    assert validated["jti"] == access_payload["jti"]


@pytest.mark.asyncio
async def test_refresh_token_cannot_be_used_as_access_token(redis_mock):
    pair = create_token_pair(42, "KOS-Test-Agent")
    with pytest.raises(AuthException) as exc_info:
        await validate_token(pair["refresh_token"], "access", "KOS-Test-Agent")
    assert exc_info.value.data["reason"] == "token_type_invalid"


@pytest.mark.asyncio
async def test_refresh_rotation_is_atomic_and_replay_revokes_user(redis_mock):
    pair = create_token_pair(42, "KOS-Test-Agent")
    refresh_payload = await validate_token(pair["refresh_token"], "refresh", "KOS-Test-Agent")

    assert await consume_refresh_token(refresh_payload) is True
    assert await consume_refresh_token(refresh_payload) is False
    await revoke_user_tokens(42)

    with pytest.raises(AuthException) as exc_info:
        await validate_token(pair["access_token"], "access", "KOS-Test-Agent")
    assert exc_info.value.data["reason"] == "token_revoked"


@pytest.mark.asyncio
async def test_user_agent_mismatch_revokes_only_current_session(redis_mock):
    first_session = create_token_pair(42, "KOS-Test-Agent-A")
    second_session = create_token_pair(42, "KOS-Test-Agent-B")

    with pytest.raises(AuthException) as exc_info:
        await validate_token(first_session["access_token"], "access", "Changed-Agent")
    assert exc_info.value.data["reason"] == "client_context_mismatch"

    with pytest.raises(AuthException) as revoked_exc:
        await validate_token(first_session["refresh_token"], "refresh", "KOS-Test-Agent-A")
    assert revoked_exc.value.data["reason"] == "token_revoked"

    assert await validate_token(second_session["access_token"], "access", "KOS-Test-Agent-B")


@pytest.mark.asyncio
async def test_expired_access_token_has_stable_reason(redis_mock):
    expired = create_access_token(
        42,
        expires_delta=timedelta(seconds=-1),
        user_agent="KOS-Test-Agent",
    )
    with pytest.raises(AuthException) as exc_info:
        await validate_token(expired, "access", "KOS-Test-Agent")
    assert exc_info.value.data["reason"] == "access_token_expired"


@pytest.mark.asyncio
async def test_redis_unavailable_fails_closed(monkeypatch):
    pair = create_token_pair(42, "KOS-Test-Agent")
    monkeypatch.setattr(RedisUtil, "_redis", None)

    with pytest.raises(ApiException) as exc_info:
        await validate_token(pair["access_token"], "access", "KOS-Test-Agent")
    assert exc_info.value.http_status == 503
    assert exc_info.value.data["reason"] == "auth_state_unavailable"
