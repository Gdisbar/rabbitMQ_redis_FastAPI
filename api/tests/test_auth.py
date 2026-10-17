import pytest


@pytest.mark.asyncio
async def test_login_success(client):
    r = await client.post(
        "/auth/login", json={"username": "alice", "password": "password123"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600

@pytest.mark.asyncio
async def test_login_bad_password(client):
    r = await client.post(
        "/auth/login", json={"username": "alice", "password": "wrong"}
    )
    assert r.status_code == 401

@pytest.mark.asyncio
async def test_login_unknown_user(client):
    r = await client.post(
        "/auth/login", json={"username": "nobody", "password": "whatever"}
    )
    assert r.status_code == 401

@pytest.mark.asyncio
async def test_logout_revokes_token(alice_client):
    assert (await alice_client.get("/me")).status_code == 200

    r = await alice_client.post("/auth/logout")
    assert r.status_code == 200

    r = await alice_client.get("/me")
    assert r.status_code == 401
    assert r.json()["detail"] == "token revoked"