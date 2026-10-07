from dataclasses import dataclass

import jwt as pyjwt
from fastapi import Depends,Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .redis_client import get_redis
from .security import decode_token

# add authorization
bearer_scheme = HTTPBearer(auto_error=False)

@dataclass
class AuthContext:
    is_authenticated: bool
    user_id: int | None
    username: str | None
    jti: str | None
    exp: int | None
    client_ip: str


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
            # Invalid / expired token → treated as guest.
            # Sprint 3 will rate-limit this fallback path aggressively.
            is_auth = False

    # Revocation check — the whole point of using Redis with JWT.
    if is_auth and jti:
        if await get_redis().exists(f"jwt:blocklist:{jti}"):
            raise HTTPException(status_code=401, detail="token revoked")

    return AuthContext(
        is_authenticated=is_auth,
        user_id=user_id,
        username=username,
        jti=jti,
        exp=exp,
        client_ip=client_ip,
    )


def require_auth(ctx: AuthContext) -> AuthContext:
    if not ctx.is_authenticated:
        raise HTTPException(status_code=401, detail="authentication required")
    return ctx