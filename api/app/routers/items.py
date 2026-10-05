from fastapi import APIRouter, HTTPException, Query

from ..db import pools
from ..schemas import ItemCreate, ItemUpdate

router = APIRouter(tags=["items"])

# NOTE: no auth yet. owner_id is hard-coded to 1 (alice) for demo purposes.
OWNER_ID = 1


@router.get("/items")
async def list_items(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    async with pools.primary.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, owner_id, name, description, created_at, updated_at
               FROM items ORDER BY id DESC LIMIT $1 OFFSET $2""",
            limit, offset,
        )
    return [dict(r) for r in rows]


@router.get("/items/{item_id}")
async def get_item(item_id: int):
    async with pools.primary.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT id, owner_id, name, description, created_at, updated_at
               FROM items WHERE id = $1""",
            item_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="item not found")
    return dict(row)


@router.post("/items", status_code=201)
async def create_item(body: ItemCreate):
    async with pools.primary.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO items (owner_id, name, description)
               VALUES ($1, $2, $3)
               RETURNING id, owner_id, name, description, created_at, updated_at""",
            OWNER_ID, body.name, body.description,
        )
    return dict(row)


@router.patch("/items/{item_id}")
async def update_item(item_id: int, body: ItemUpdate):
    async with pools.primary.acquire() as conn:
        row = await conn.fetchrow(
            """UPDATE items
                  SET name        = COALESCE($1, name),
                      description = COALESCE($2, description),
                      updated_at  = now()
                WHERE id = $3
                RETURNING id, owner_id, name, description, created_at, updated_at""",
            body.name, body.description, item_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="item not found")
    return dict(row)


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int):
    async with pools.primary.acquire() as conn:
        res = await conn.execute("DELETE FROM items WHERE id = $1", item_id)
    if res.endswith(" 0"):
        raise HTTPException(status_code=404, detail="item not found")
    return None