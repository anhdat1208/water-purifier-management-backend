from __future__ import annotations

from redis import Redis
from redis.exceptions import RedisError

from app.config import settings

_redis: Redis | None = None
_memory_refresh_tokens: dict[str, str] = {}
_use_memory_fallback = False


def _ensure_redis() -> Redis | None:
    global _redis, _use_memory_fallback
    if _use_memory_fallback:
        return None
    if _redis is None:
        try:
            client = Redis.from_url(settings.redis_url, decode_responses=True)
            client.ping()
            _redis = client
        except RedisError:
            _use_memory_fallback = True
    return _redis


def store_refresh_token(jti: str, user_id: str, ttl_seconds: int) -> None:
    client = _ensure_redis()
    if client:
        client.setex(f"refresh:{jti}", ttl_seconds, user_id)
    else:
        _memory_refresh_tokens[jti] = user_id


def is_refresh_token_valid(jti: str) -> bool:
    client = _ensure_redis()
    if client:
        return client.exists(f"refresh:{jti}") == 1
    return jti in _memory_refresh_tokens


def revoke_refresh_token(jti: str) -> None:
    client = _ensure_redis()
    if client:
        client.delete(f"refresh:{jti}")
    else:
        _memory_refresh_tokens.pop(jti, None)
