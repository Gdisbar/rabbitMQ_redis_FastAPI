from fastapi import APIRouter, Depends, HTTPException

from ..db import pools
from ..deps import AuthContext, auth_and_rate_limit, require_auth
from ..deps import auth_and_rate_limit

# inject auth-rate-limiting dependency
router = APIRouter(tags=["me"], dependencies=[Depends(auth_and_rate_limit)])



@router.get("/me")
async def me(ctx: AuthContext = Depends(auth_and_rate_limit)):
    ctx = require_auth(ctx)
    async with pools.primary.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, username, created_at FROM users WHERE id = $1",
            ctx.user_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="user not found")
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM items WHERE owner_id = $1", ctx.user_id
        )
    d = dict(row)
    d["item_count"] = count
    return d