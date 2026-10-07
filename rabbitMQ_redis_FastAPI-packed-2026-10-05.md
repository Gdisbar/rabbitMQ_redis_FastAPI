# 📁 Project: rabbitMQ_redis_FastAPI

**📊 Project Overview (Selected Files):**
- Total Files: 12
- Total Size: 7.32 KB
- Total Lines: 255
- Estimated Tokens: ~1,878 (approx. for LLMs)

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
Size: 440 B | Lines: 18
================================================================================

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    pg_primary_dsn: str = "postgresql://app:app_pass@pg-primary:5432/appdb"

    redis_url: str = "redis://redis:6379/0"

    jwt_secret: str = "K2yBfQFgPnFvCBecUHHqb4h8geNPs3aqsvs4N1A9ouA"
    jwt_alg: str = "HS256"
    jwt_ttl_seconds: int = 3600

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
Size: 651 B | Lines: 28
================================================================================

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .db import pools
from .redis_client import init_redis, close_redis
from .routers import auth, items, me


@asynccontextmanager
async def lifespan(app: FastAPI):
    await pools.init(settings.pg_primary_dsn)
    await init_redis()
    yield
    await close_redis()
    await pools.close()


app = FastAPI(title="FastAPI CRUD + Auth (HA)", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(items.router)
app.include_router(me.router)


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
Size: 3.11 KB | Lines: 88
================================================================================

```python
from fastapi import APIRouter, Depends, HTTPException, Query

from ..db import pools
from ..deps import AuthContext, auth_and_rate_limit, require_auth
from ..schemas import ItemCreate, ItemUpdate
from ..deps import auth_and_rate_limit

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
        raise HTTPException(status_code=404, detail="item not found")
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
        raise HTTPException(status_code=404, detail="item not found or not owned by user")
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
        raise HTTPException(status_code=404, detail="item not found or not owned by user")
    return None
```

================================================================================
📄 **api\app\schemas.py**
Size: 479 B | Lines: 21
================================================================================

```python
from pydantic import BaseModel, Field

class LoginIn(BaseModel):
    username: str
    password: str


class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


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
Size: 146 B | Lines: 8
================================================================================

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
pydantic==2.9.2
pydantic-settings==2.6.0
asyncpg==0.30.0
redis==5.2.0
PyJWT==2.9.0
bcrypt==4.2.0
```

================================================================================
📄 **docker-compose.yml**
Size: 1.09 KB | Lines: 42
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
      - ./postgres/seed.sql:/docker-entrypoint-initdb.d/seed.sql:ro
      - pg_primary_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d appdb -h 127.0.0.1"]
      interval: 5s
      timeout: 5s
      retries: 30

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 20

  api:
    build: ./api
    ports: ["8000:8000"]
    environment:
      PG_PRIMARY_DSN: postgresql://user123:app_pwd123@pg-primary:5432/appdb
      REDIS_URL: redis://redis:6379/0
      JWT_SECRET: "K2yBfQFgPnFvCBecUHHqb4h8geNPs3aqsvs4N1A9ouA"
      JWT_TTL_SECONDS: "3600"
    depends_on:
      pg-primary: { condition: service_healthy }
      redis:      { condition: service_healthy }

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
*Total files processed: 12 | Generated on: 10/7/2026, 9:14:43 AM*
