import os
from typing import AsyncIterator
import pytest
import httpx
import pytest_asyncio

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

@pytest.mark.asyncio
async def _login(username: str, password: str) -> str:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as c:
        r = await c.post(
            "/auth/login", json={"username": username, "password": password}
        )
        r.raise_for_status()
        return r.json()["access_token"]

# @pytest.mark.asyncio
@pytest_asyncio.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as c:
        yield c

# @pytest.mark.asyncio
@pytest_asyncio.fixture
async def alice_client() -> AsyncIterator[httpx.AsyncClient]:
    token = await _login("alice", "password123")
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=10.0,
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        yield c

# @pytest.mark.asyncio
@pytest_asyncio.fixture
async def bob_client() -> AsyncIterator[httpx.AsyncClient]:
    token = await _login("bob", "password123")
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=10.0,
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        yield c