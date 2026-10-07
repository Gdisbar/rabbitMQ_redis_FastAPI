import time

import bcrypt
from fastapi import APIRouter, Depends, HTTPException

from ..config import settings
from ..db import pools
from ..deps import AuthContext, auth_and_rate_limit, require_auth
from ..redis_client import get_redis
from ..schemas import LoginIn, LoginOut
from ..security import create_token
from ..deps import auth_and_rate_limit

router = APIRouter(prefix="/auth", tags=["auth"],dependencies=[Depends(auth_and_rate_limit)])


@router.post("/login", response_model=LoginOut)
async def login(body: LoginIn):
    async with pools.primary.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, username, password_hash FROM users WHERE username = $1",
            body.username,
        )
    if not user or not bcrypt.checkpw(
        body.password.encode("utf-8"),
        user["password_hash"].encode("utf-8"),
    ):
        raise HTTPException(status_code=401, detail="invalid credentials")

    token, _jti, _exp = create_token(user["id"], user["username"])
    return LoginOut(access_token=token, expires_in=settings.jwt_ttl_seconds)


@router.post("/logout")
async def logout(ctx: AuthContext = Depends(auth_and_rate_limit)):
    ctx = require_auth(ctx)
    remaining = max(1, int((ctx.exp or 0) - time.time()))
    await get_redis().set(f"jwt:blocklist:{ctx.jti}", "1", ex=remaining)
    return {"ok": True, "revoked_jti": ctx.jti, "ttl": remaining}