import pytest

@pytest.mark.asyncio
async def test_me_requires_auth(client):
    r = await client.get("/me")
    assert r.status_code == 401

@pytest.mark.asyncio
async def test_me_returns_profile_and_item_count(alice_client):
    r = await alice_client.get("/me")
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "alice"
    assert isinstance(body["item_count"], int)