from pathlib import Path

import redis.asyncio as aioredis

from .config import settings

_redis: aioredis.Redis | None = None
_rl_script = None

_LUA_PATH = Path(__file__).parent / "ratelimit.lua"


async def init_redis() -> None:
    global _redis, _rl_script
    _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    await _redis.ping()
    # SHA-registered on the server; subsequent calls just send the digest.
    _rl_script = _redis.register_script(_LUA_PATH.read_text())


async def close_redis() -> None:
    if _redis is not None:
        await _redis.aclose()


def get_redis() -> aioredis.Redis:
    assert _redis is not None, "redis not initialised"
    return _redis


def rl_script():
    assert _rl_script is not None, "lua script not loaded"
    return _rl_script