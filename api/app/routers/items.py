from fastapi import APIRouter, Depends, HTTPException, Query

from ..db import pools
from ..deps import AuthContext, auth_and_rate_limit, require_auth
from ..schemas import ItemCreate, ItemUpdate

import logging
from opentelemetry import metrics

logger = logging.getLogger("fastapi-crud")
meter = metrics.get_meter_provider().get_meter(__name__)

# ---- Custom counters ----
item_create_counter = meter.create_counter(
    "items.created",
    description="Number of items created",
    unit="1",
)
item_update_counter = meter.create_counter(
    "items.updated",
    description="Number of items updated",
    unit="1",
)
item_delete_counter = meter.create_counter(
    "items.deleted",
    description="Number of items deleted",
    unit="1",
)
item_list_counter = meter.create_counter(
    "items.listed",
    description="Number of item list requests",
    unit="1",
)
item_get_counter = meter.create_counter(
    "items.fetched",
    description="Number of single item fetches",
    unit="1",
)
item_not_found_counter = meter.create_counter(
    "items.not_found",
    description="Number of item lookups that returned 404",
    unit="1",
)

# inject auth-rate-limiting dependency
router = APIRouter(tags=["items"], dependencies=[Depends(auth_and_rate_limit)])


@router.get("/items")
async def list_items(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    ctx: AuthContext = Depends(auth_and_rate_limit),
):
    async with pools.primary.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, owner_id, name, description, created_at, updated_at
               FROM items ORDER BY id DESC LIMIT $1 OFFSET $2""",
            limit, offset,
        )

    item_list_counter.add(
        1,
        {
            "user_id": str(ctx.user_id) if ctx.user_id else "anonymous",
            "is_authenticated": str(ctx.is_authenticated),
            "result_count": str(len(rows)),
        },
    )
    logger.info(
        "Items listed",
        extra={
            "user_id": ctx.user_id,
            "is_authenticated": ctx.is_authenticated,
            "limit": limit,
            "offset": offset,
            "result_count": len(rows),
        },
    )
    return [dict(r) for r in rows]


@router.get("/items/{item_id}")
async def get_item(item_id: int, ctx: AuthContext = Depends(auth_and_rate_limit)):
    async with pools.primary.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT id, owner_id, name, description, created_at, updated_at
               FROM items WHERE id = $1""",
            item_id,
        )
    if not row:
        item_not_found_counter.add(1, {"item_id": str(item_id)})
        logger.warning(
            "Item not found",
            extra={"item_id": item_id, "user_id": ctx.user_id},
        )
        raise HTTPException(status_code=404, detail="item not found")

    item_get_counter.add(
        1,
        {
            "item_id": str(item_id),
            "owner_id": str(row["owner_id"]),
            "user_id": str(ctx.user_id) if ctx.user_id else "anonymous",
        },
    )
    logger.info(
        "Item fetched",
        extra={"item_id": item_id, "owner_id": row["owner_id"], "user_id": ctx.user_id},
    )
    return dict(row)


@router.post("/items", status_code=201)
async def create_item(
    body: ItemCreate,
    ctx: AuthContext = Depends(auth_and_rate_limit),
):
    ctx = require_auth(ctx)
    async with pools.primary.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO items (owner_id, name, description)
               VALUES ($1, $2, $3)
               RETURNING id, owner_id, name, description, created_at, updated_at""",
            ctx.user_id, body.name, body.description,
        )

    # Emit a custom metric
    item_create_counter.add(
        1,
        {
            "user_id": str(ctx.user_id),
            "has_description": str(body.description is not None),
        },
    )
    # Structured log with custom dimensions
    logger.info(
        "Item created",
        extra={"item_id": row["id"], "owner_id": ctx.user_id, "item_name": body.name},
    )
    
    return dict(row)


@router.patch("/items/{item_id}")
async def update_item(
    item_id: int,
    body: ItemUpdate,
    ctx: AuthContext = Depends(auth_and_rate_limit),
):
    ctx = require_auth(ctx)
    async with pools.primary.acquire() as conn:
        row = await conn.fetchrow(
            """UPDATE items
                  SET name        = COALESCE($1, name),
                      description = COALESCE($2, description),
                      updated_at  = now()
                WHERE id = $3 AND owner_id = $4
                RETURNING id, owner_id, name, description, created_at, updated_at""",
            body.name, body.description, item_id, ctx.user_id,
        )
    if not row:
        item_not_found_counter.add(
            1, {"item_id": str(item_id), "op": "patch"}
        )
        logger.warning(
            "Item update failed (not found or not owned)",
            extra={"item_id": item_id, "user_id": ctx.user_id},
        )
        raise HTTPException(status_code=404, detail="item not found or not owned by user")

    item_update_counter.add(
        1,
        {
            "item_id": str(item_id),
            "user_id": str(ctx.user_id),
            "name_changed": str(body.name is not None),
            "description_changed": str(body.description is not None),
        },
    )
    logger.info(
        "Item updated",
        extra={
            "item_id": item_id,
            "owner_id": ctx.user_id,
            "name_changed": body.name is not None,
            "description_changed": body.description is not None,
        },
    )
    return dict(row)


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int, ctx: AuthContext = Depends(auth_and_rate_limit)):
    ctx = require_auth(ctx)
    async with pools.primary.acquire() as conn:
        res = await conn.execute(
            "DELETE FROM items WHERE id = $1 AND owner_id = $2",
            item_id, ctx.user_id,
        )
    if res.endswith(" 0"):
        item_not_found_counter.add(
            1, {"item_id": str(item_id), "op": "delete"}
        )
        logger.warning(
            "Item delete failed (not found or not owned)",
            extra={"item_id": item_id, "user_id": ctx.user_id},
        )
        raise HTTPException(status_code=404, detail="item not found or not owned by user")

    item_delete_counter.add(
        1,
        {"item_id": str(item_id), "user_id": str(ctx.user_id)},
    )
    logger.info(
        "Item deleted",
        extra={"item_id": item_id, "owner_id": ctx.user_id},
    )
    return None