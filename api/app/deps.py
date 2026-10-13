import time
from dataclasses import dataclass

import jwt as pyjwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings
from .redis_client import rl_script
from .security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    is_authenticated: bool
    user_id: int | None
    username: str | None
    jti: str | None
    exp: int | None
    client_ip: str
    rate_limit_remaining: int   # NEW — informational; handy for headers later


async def auth_and_rate_limit(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthContext:
    client_ip = request.client.host if request.client else "unknown"

    user_id = username = jti = None
    exp = None
    is_auth = False

    if creds is not None and creds.scheme.lower() == "bearer":
        try:
            claims = decode_token(creds.credentials)
            user_id = int(claims["sub"])
            username = claims.get("username")
            jti = claims.get("jti")
            exp = int(claims.get("exp", 0))
            is_auth = True
        except pyjwt.PyJWTError:
            # Bad/expired token → fall back to guest bucket (strict).
            is_auth = False

    if is_auth:
        rl_key = f"rl:user:{user_id}"
        limit = settings.rl_auth_limit
        window = settings.rl_auth_window_ms
        blocklist_key = f"jwt:blocklist:{jti}"
        has_jti = 1
    else:
        rl_key = f"rl:ip:{client_ip}"
        limit = settings.rl_unauth_limit
        window = settings.rl_unauth_window_ms
        blocklist_key = "jwt:blocklist:__n/a__"
        has_jti = 0

    now_ms = int(time.time() * 1000)
    allowed, count, reason = await rl_script()(
        keys=[rl_key, "rl:burst:global", blocklist_key],
        args=[
            now_ms, window, limit,
            settings.rl_burst_limit, settings.rl_burst_window_ms,
            has_jti,
        ],
    )

    if not allowed:
        if reason == "blocked":
            raise HTTPException(status_code=401, detail="token revoked")
        raise HTTPException(
            status_code=429,
            detail=f"rate limit exceeded ({reason})",
            headers={"Retry-After": "60"},
        )

    remaining = max(0, limit - int(count))
    return AuthContext(
        is_authenticated=is_auth,
        user_id=user_id,
        username=username,
        jti=jti,
        exp=exp,
        client_ip=client_ip,
        rate_limit_remaining=remaining,
    )


def require_auth(ctx: AuthContext) -> AuthContext:
    if not ctx.is_authenticated:
        raise HTTPException(status_code=401, detail="authentication required")
    return ctx