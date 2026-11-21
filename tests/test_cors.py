def test_preflight_allows_frontend_origin(client):
    res = client.options(
        "/applications",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_unknown_origin_not_allowed(client):
    res = client.get("/applications", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in res.headers
