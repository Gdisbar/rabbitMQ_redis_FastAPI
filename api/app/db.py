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