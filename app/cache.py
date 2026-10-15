import json

import redis

from app.config import settings

_client = redis.Redis.from_url(
    settings.redis_url,
    socket_connect_timeout=1,
    socket_timeout=1,
    decode_responses=True,
)


def _stats_key(user_id: int) -> str:
    return f"stats:{user_id}"


def get_cached_stats(user_id: int) -> dict | None:
    try:
        value = _client.get(_stats_key(user_id))
        return json.loads(value) if value else None
    except redis.RedisError:
        return None


def set_cached_stats(user_id: int, data: dict, ttl: int = 60) -> None:
    try:
        _client.set(_stats_key(user_id), json.dumps(data), ex=ttl)
    except redis.RedisError:
        pass


def invalidate_stats(user_id: int) -> None:
    try:
        _client.delete(_stats_key(user_id))
    except redis.RedisError:
        pass