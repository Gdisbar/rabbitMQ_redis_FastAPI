# 📁 Project: rabbitMQ_redis_FastAPI

**📊 Project Overview (Selected Files):**
- Total Files: 12
- Total Size: 5.8 KB
- Total Lines: 204
- Estimated Tokens: ~1,488 (approx. for LLMs)

**📋 Top File Types:**
- .py: 8
- (no ext): 1
- .txt: 1
- .yml: 1
- .sql: 1

🔖 Legend: ✓=included · ✗=excluded · 📂=folder

## 🌳 Project Structure

```
rabbitMQ_redis_FastAPI/
├── 📂 api/
│   ├── 📂 app/
│   │   ├── 📂 routers/
│   │   │   ├── __init__.py ✓
│   │   │   └── items.py ✓
│   │   ├── __init__.py ✓
│   │   ├── config.py ✓
│   │   ├── db.py ✓
│   │   ├── main.py ✓
│   │   └── schemas.py ✓
│   ├── __init__.py ✓
│   ├── Dockerfile ✓
│   └── requirements.txt ✓
├── 📂 postgres/
│   └── seed.sql ✓
└── docker-compose.yml ✓
```

## 📄 Files Content

*Files are listed in alphabetical order by path.*

================================================================================
📄 **api\__init__.py**
Size: 0 B | Lines: 1
================================================================================

```python

```

================================================================================
📄 **api\app\__init__.py**
Size: 0 B | Lines: 1
================================================================================

```python

```

================================================================================
📄 **api\app\config.py**
Size: 261 B | Lines: 12
================================================================================

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    pg_primary_dsn: str = "postgresql://user123:app_pwd123@pg-primary:5432/appdb"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
```

================================================================================
📄 **api\app\db.py**
Size: 398 B | Lines: 16
================================================================================

```python
import asyncpg


class DBPools:
    def __init__(self) -> None:
        self.primary: asyncpg.Pool | None = None

    async def init(self, primary_dsn: str) -> None:
        self.primary = await asyncpg.create_pool(primary_dsn, min_size=1, max_size=8)

    async def close(self) -> None:
        if self.primary is not None:
            await self.primary.close()


pools = DBPools()
```

================================================================================
📄 **api\app\main.py**
Size: 475 B | Lines: 22
================================================================================

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

from .config import settings
from .db import pools
from .routers import items


@asynccontextmanager
async def lifespan(app: FastAPI):
    await pools.init(settings.pg_primary_dsn)
    yield
    await pools.close()


app = FastAPI(title="FastAPI CRUD + Auth (HA)", lifespan=lifespan)
app.include_router(items.router)


@app.get("/health")
async def health():
    return {"ok": True}
```

================================================================================
📄 **api\app\routers\__init__.py**
Size: 0 B | Lines: 1
================================================================================

```python

```

================================================================================
📄 **api\app\routers\items.py**
Size: 2.5 KB | Lines: 74
================================================================================

```python
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
```

================================================================================
📄 **api\app\schemas.py**
Size: 304 B | Lines: 11
================================================================================

```python
from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class ItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
```

================================================================================
📄 **api\Dockerfile**
Size: 257 B | Lines: 8
================================================================================

```
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

================================================================================
📄 **api\requirements.txt**
Size: 103 B | Lines: 5
================================================================================

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
pydantic==2.9.2
pydantic-settings==2.6.0
asyncpg==0.30.0
```

================================================================================
📄 **docker-compose.yml**
Size: 746 B | Lines: 30
================================================================================

```yaml
name: fastapi-crud-ha

services:
  pg-primary:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: user123
      POSTGRES_PASSWORD: app_pwd123
      POSTGRES_DB: appdb
    ports: ["5432:5432"]
    volumes:
      - - ./postgres/seed.sql:/docker-entrypoint-initdb.d/seed.sql:ro
      - pg_primary_data:/var/lib/postgresql/data
    
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d appdb -h 127.0.0.1"]
      interval: 5s
      timeout: 5s
      retries: 30

  api:
    build: ./api
    ports: ["8000:8000"]
    environment:
      PG_PRIMARY_DSN: postgresql://user123:app_pwd123@pg-primary:5432/appdb
    depends_on:
      pg-primary: { condition: service_healthy }

volumes:
  pg_primary_data:
```

================================================================================
📄 **postgres\seed.sql**
Size: 833 B | Lines: 23
================================================================================

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id            BIGSERIAL PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS items (
    id          BIGSERIAL PRIMARY KEY,
    owner_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_items_owner ON items(owner_id);

INSERT INTO users (username, password_hash) VALUES
  ('alice', crypt('password123', gen_salt('bf', 12))),
  ('bob',   crypt('password123', gen_salt('bf', 12)))
ON CONFLICT (username) DO NOTHING;
```

---
*Generated by Codebase Prompt Packer for VS Code*
*Total files processed: 12 | Generated on: 10/5/2026, 1:24:49 PM*
