import pytest

@pytest.mark.asyncio
async def test_list_items_without_auth_is_public(client):
    # Characterization: today GET /items works for guests. M3 will revisit this.
    r = await client.get("/items")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

@pytest.mark.asyncio
async def test_create_item_requires_auth(client):
    r = await client.post("/items", json={"name": "x"})
    assert r.status_code == 401

@pytest.mark.asyncio
async def test_create_get_delete_roundtrip(alice_client):
    r = await alice_client.post(
        "/items", json={"name": "m1-roundtrip", "description": "desc"}
    )
    assert r.status_code == 201
    item = r.json()
    item_id = item["id"]
    assert item["name"] == "m1-roundtrip"
    assert item["owner_id"] is not None

    r = await alice_client.get(f"/items/{item_id}")
    assert r.status_code == 200
    assert r.json()["id"] == item_id

    r = await alice_client.delete(f"/items/{item_id}")
    assert r.status_code == 204

@pytest.mark.asyncio
async def test_bob_cannot_modify_alice_item(alice_client, bob_client):
    r = await alice_client.post("/items", json={"name": "owned-by-alice"})
    item_id = r.json()["id"]

    r = await bob_client.patch(f"/items/{item_id}", json={"name": "stolen"})
    assert r.status_code == 404

    r = await bob_client.delete(f"/items/{item_id}")
    assert r.status_code == 404

    # alice still owns and can delete it
    await alice_client.delete(f"/items/{item_id}")

@pytest.mark.asyncio
async def test_get_missing_item_is_404(alice_client):
    r = await alice_client.get("/items/999999999")
    assert r.status_code == 404