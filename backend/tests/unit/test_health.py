"""Phase 1: /api/v1/health serves liveness + DB + weather mode + vision chain."""


def test_health_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"
    assert body["weather_mode"] == "replay"  # from backend/.env
    assert isinstance(body["time_utc"], str)


def test_health_reports_vision_chain_in_configured_order(client):
    body = client.get("/api/v1/health").json()
    providers = [entry["provider"] for entry in body["vision_chain"]]
    assert providers == ["cache", "gemini"]
    cache_entry = body["vision_chain"][0]
    assert cache_entry["configured"] is True


def test_openapi_docs_served(client):
    response = client.get("/docs")
    assert response.status_code == 200


def test_unknown_route_is_404_envelope(client):
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "HTTP_404"