import re


def test_create_application(make_application):
    app = make_application()
    assert app["current_stage"] == "New"
    assert re.fullmatch(r"thank-you-from-b12-\d{17}-[0-9a-f]{12}", app["receipt"])
    assert app["timestamp"]


def test_receipts_are_unique(make_application):
    assert make_application()["receipt"] != make_application()["receipt"]


def test_create_rejects_bad_input(client):
    for body in [
        {"name": "A", "email": "not-an-email"},
        {"name": "A", "email": "a@example.com", "applicant_name": "typo"},
        {"name": "A", "email": "a@example.com", "resume_link": "not a url"},
        {"name": "A", "email": "a@example.com", "timestamp": "2026-01-01T00:00:00"},
        {"name": "   ", "email": "a@example.com"},
        {"email": "a@example.com"},
        {},
    ]:
        assert client.post("/applications", json=body).status_code == 422


def test_get_application(client, make_application):
    created = make_application()
    res = client.get(f"/applications/{created['id']}")
    assert res.status_code == 200
    assert res.json() == {k: v for k, v in created.items() if k != "success"}


def test_unknown_application_is_404_everywhere(client):
    assert client.get("/applications/999").status_code == 404
    assert client.get("/applications/999/history").status_code == 404
    assert client.put("/applications/999/stage", json={"stage": "Hired"}).status_code == 404
    assert client.post("/applications/999/notes", json={"content": "x"}).status_code == 404


def test_non_integer_id_is_422(client):
    assert client.get("/applications/abc").status_code == 422
