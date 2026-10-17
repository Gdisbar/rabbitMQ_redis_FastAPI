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
    
    await pools.init(settings.pg_primary_dsn.get_secret_value())
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