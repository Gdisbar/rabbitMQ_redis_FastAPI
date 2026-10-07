import redis.asyncio as aioredis

from .config import settings

_redis: aioredis.Redis | None = None


async def init_redis() -> None:
    global _redis
    _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    await _redis.ping()


async def close_redis() -> None:
    if _redis is not None:
        await _redis.aclose()


def get_redis() -> aioredis.Redis:
    assert _redis is not None, "redis not initialised"
    return _redis