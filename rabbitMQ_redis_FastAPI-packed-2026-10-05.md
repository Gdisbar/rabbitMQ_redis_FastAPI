# 📁 Project: rabbitMQ_redis_FastAPI

**📊 Project Overview (Selected Files):**
- Total Files: 19
- Total Size: 22.25 KB
- Total Lines: 732
- Estimated Tokens: ~5,641 (approx. for LLMs)

**📋 Top File Types:**
- .py: 14
- (no ext): 1
- .txt: 1
- .yml: 1
- .sql: 1
- .md: 1

🔖 Legend: ✓=included · ✗=excluded · 📂=folder

## 🌳 Project Structure

```
rabbitMQ_redis_FastAPI/
├── 📂 api/
│   ├── 📂 app/
│   │   ├── 📂 routers/
│   │   │   ├── __init__.py ✓
│   │   │   ├── auth.py ✓
│   │   │   ├── items.py ✓
│   │   │   └── me.py ✓
│   │   ├── __init__.py ✓
│   │   ├── config.py ✓
│   │   ├── db.py ✓
│   │   ├── deps.py ✓
│   │   ├── main.py ✓
│   │   ├── redis_client.py ✓
│   │   ├── schemas.py ✓
│   │   ├── security.py ✓
│   │   └── telemetry.py ✓
│   ├── __init__.py ✓
│   ├── Dockerfile ✓
│   └── requirements.txt ✓
├── 📂 postgres/
│   └── seed.sql ✓
├── docker-compose.yml ✓
└── README.md ✓
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
Size: 1.91 KB | Lines: 58
================================================================================

```python
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---- Database ----
    # No default → app will fail fast if not provided in production.
    pg_primary_dsn: SecretStr = Field(..., description="Postgres DSN")

    # ---- Redis ----
    redis_url: str = "redis://redis:6379/0"

    # ---- JWT ----
    jwt_secret: SecretStr = Field(..., min_length=32)
    jwt_alg: str = "HS256"
    jwt_ttl_seconds: int = Field(3600, ge=60, le=86_400)

    # ---- Rate limits ----
    rl_unauth_limit: int = 1
    rl_unauth_window_ms: int = 60_000
    rl_auth_limit: int = 15
    rl_auth_window_ms: int = 60_000
    rl_burst_limit: int = 800
    rl_burst_window_ms: int = 1_000

    # ---- Application Insights ----
    applicationinsights_connection_string: SecretStr | None = None
    applicationinsights_enabled: bool = False

    # ---- Environment ----
    environment: str = Field("dev", pattern="^(dev|staging|prod)$")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",          # ignore unrelated env vars
    )

    # ---- Validators ----
    @field_validator("jwt_secret")
    @classmethod
    def _jwt_secret_strength(cls, v: SecretStr) -> SecretStr:
        raw = v.get_secret_value()
        # Reject obviously weak secrets
        if raw.lower() in {"secret", "changeme", "password", "test"}:
            raise ValueError("jwt_secret is too weak")
        return v

    @field_validator("applicationinsights_connection_string")
    @classmethod
    def _ai_required_if_enabled(cls, v, info):
        # If AI is enabled, the connection string must be present.
        # (Runs after `enabled` in field order — see model_validator below if you reorder.)
        return v


settings = Settings()
```

================================================================================
📄 **api\app\db.py**
Size: 457 B | Lines: 16
================================================================================

```python
import asyncpg
from .config import settings

class DBPools:
    def __init__(self) -> None:
        self.primary: asyncpg.Pool | None = None

    async def init(self, primary_dsn: str) -> None:
        self.primary = await asyncpg.create_pool(settings.pg_primary_dsn.get_secret_value(), min_size=1, max_size=8)

    async def close(self) -> None:
        if self.primary is not None:
            await self.primary.close()


pools = DBPools()
```

================================================================================
📄 **api\app\deps.py**
Size: 1.89 KB | Lines: 63
================================================================================

```python
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
```

================================================================================
📄 **api\app\main.py**
Size: 924 B | Lines: 41
================================================================================

```python
from .telemetry import setup_telemetry
# Import the instrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# add telemetry @ start
setup_telemetry() 


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

# Explicitly instrument the app
FastAPIInstrumentor.instrument_app(app)

app.include_router(auth.router)
app.include_router(items.router)
app.include_router(me.router)


@app.get("/health")
async def health():
    return {"ok": True}
```

================================================================================
📄 **api\app\redis_client.py**
Size: 472 B | Lines: 21
================================================================================

```python
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
```

================================================================================
📄 **api\app\routers\__init__.py**
Size: 0 B | Lines: 1
================================================================================

```python

```

================================================================================
📄 **api\app\routers\auth.py**
Size: 1.41 KB | Lines: 39
================================================================================

```python
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
```

================================================================================
📄 **api\app\routers\items.py**
Size: 6.76 KB | Lines: 218
================================================================================

```python
from fastapi import APIRouter, Depends, HTTPException, Query

from ..db import pools
from ..deps import AuthContext, auth_and_rate_limit, require_auth
from ..schemas import ItemCreate, ItemUpdate

import logging
from opentelemetry import metrics

logger = logging.getLogger("fastapi-crud-ha")
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
        extra={"item_id": row["id"], "owner_id": ctx.user_id, "name": body.name},
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
```

================================================================================
📄 **api\app\routers\me.py**
Size: 902 B | Lines: 27
================================================================================

```python
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
📄 **api\app\security.py**
Size: 869 B | Lines: 30
================================================================================

```python
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from .config import settings


def create_token(user_id: int, username: str) -> tuple[str, str, int]:
    """Returns (token, jti, exp_epoch)."""
    jti = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    exp = int((now + timedelta(seconds=settings.jwt_ttl_seconds)).timestamp())
    payload = {
        "sub": str(user_id),
        "username": username,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": exp,
    }
    token = jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_alg)
    return token, jti, exp


def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.jwt_secret.get_secret_value(),   # unwrap SecretStr
        algorithms=[settings.jwt_alg],
    )
```

================================================================================
📄 **api\app\telemetry.py**
Size: 1.02 KB | Lines: 20
================================================================================

```python
import logging
from azure.monitor.opentelemetry import configure_azure_monitor
from .config import settings

def setup_telemetry() -> None:
    """Initialize Azure Monitor OpenTelemetry."""
    if not settings.applicationinsights_enabled and settings.applicationinsights_connection_string:
        return
    if not settings.applicationinsights_connection_string:
        logging.warning("Application Insights enabled but no connection string provided")
        return
    if settings.applicationinsights_enabled and settings.applicationinsights_connection_string:
        configure_azure_monitor(
            connection_string=settings.applicationinsights_connection_string.get_secret_value(),
            logger_name="fastapi-crud-ha",  # custom logger name to avoid duplicates
            disable_offline_storage=True,   # optional: prevents local file storage issues in containers
        )

    # Reduce noise: disable uvicorn access logs from being duplicated
    logging.getLogger("uvicorn.access").propagate = False
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
Size: 182 B | Lines: 9
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
azure-monitor-opentelemetry==1.8.2
```

================================================================================
📄 **docker-compose.yml**
Size: 1.16 KB | Lines: 44
================================================================================

```yaml
name: fastapi-crud-ha

services:
  pg-primary:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${PG_USER}
      POSTGRES_PASSWORD: ${PG_PASSWD}
      POSTGRES_DB: appdb
    ports: ["5432:5432"]
    volumes:
      - ./postgres/seed.sql:/docker-entrypoint-initdb.d/seed.sql:ro
      - pg_primary_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user123 -d appdb -h 127.0.0.1"]
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
      PG_PRIMARY_DSN: ${PG_PRIMARY_DSN}
      REDIS_URL: redis://redis:6379/0
      JWT_SECRET: ${JWT_SECRET}
      JWT_TTL_SECONDS: "3600"
      APPLICATIONINSIGHTS_CONNECTION_STRING: ${APPLICATIONINSIGHTS_CONNECTION_STRING}
      APPLICATIONINSIGHTS_ENABLED: "true"
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

================================================================================
📄 **README.md**
Size: 2.85 KB | Lines: 91
================================================================================

```markdown

## Sprint-1

**Start the Instance**

```bash
# delete volume & any broken pg_primary data
docker compose down -v
# start instance
docker compose up --build -d 
# check logs - in pgadmin4 
docker compose logs -f pg-primary
# test on docker (pg-primary: The specific service/container name defined in your docker-compose.yml)
docker compose exec pg-primary psql -U app -d appdb -c "SELECT id, username FROM users;"
# testing on postman
localhost:8000/health

```

## Sprint -2

```python
import secrets
# URL-Safe Base64 Token - put it in config.py,docker-compose.yml
url_token = secrets.token_urlsafe(32)
# Here it's - Bearer K2yBfQFgPnFvCBecUHHqb4h8geNPs3aqsvs4N1A9ouA
```

iat, jti, exp, and sub are standard registered claims used in the payload of a JSON Web Token (JWT) to convey specific metadata about the token and the user

    • iat (Issued At): Records the Unix timestamp of when the token was created, helping systems calculate the token's age.
    • jti (JWT ID): Provides a unique string identifier for the token, typically used to prevent replay attacks or handle token revocation.
    • exp (Expiration Time): Sets the Unix timestamp after which the token becomes invalid and must be rejected.
    • sub (Subject): Identifies the principal entity the token is about, usually representing the unique user ID

```bash
# remove previous volume (if getting error)
docker compose down 
docker compose up --build -d
docker compose logs -f api 

# re-building particular part
docker compose up -d --build api

# get registered users (seed.sql)
docker compose exec pg-primary psql -U user123 -d appdb -c "SELECT id, username, left(password_hash,7) AS hash_prefix FROM users;"

# First use the Bearer token & get the JWT token per user (alice,bob) 
# - then login using JWT , when loged in for a particular user
# you have view access to other user but can't PATCH,DELETE entry
# created by other user
```



```bash
.
├── docker-compose.yml
├── README.md
├── postgres/
│   └── seed.sql
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── config.py
│       ├── security.py
│       ├── redis_client.py
│       ├── ratelimit.lua
│       ├── rabbit.py
│       ├── deps.py
│       ├── schemas.py
│       ├── main.py
│       └── routers/
│           ├── __init__.py
│           ├── auth.py
│           ├── items.py
│           └── me.py
└── worker/
    ├── Dockerfile
    ├── requirements.txt
    └── worker/
        ├── __init__.py
        ├── config.py
        ├── db.py
        ├── breaker.py
        ├── handlers.py
        └── main.py

```
```

---
*Generated by Codebase Prompt Packer for VS Code*
*Total files processed: 19 | Generated on: 10/15/2026, 10:09:51 AM*
