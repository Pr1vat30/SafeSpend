async def test_liveness(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["data"] == {"status": "ok"}
