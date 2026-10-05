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