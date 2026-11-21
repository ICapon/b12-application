import uuid


def test_full_candidate_lifecycle(http, new_application):
    app = new_application(name="Grace Hopper")
    app_id = http.get(f"/applications/{app['id']}").json()["id"]
    assert app["current_stage"] == "New"

    # note on "New", move forward, note on the new stage
    assert http.post(f"/applications/{app_id}/notes", json={"content": "Strong resume"}).status_code == 201
    assert http.put(f"/applications/{app_id}/stage", json={"stage": "Phone screen scheduled"}).status_code == 200
    assert http.post(f"/applications/{app_id}/notes", json={"content": "Call on Monday"}).status_code == 201
    assert http.put(f"/applications/{app_id}/stage", json={"stage": "Interview scheduled"}).status_code == 200
    assert http.put(f"/applications/{app_id}/stage", json={"stage": "Hired"}).status_code == 200

    detail = http.get(f"/applications/{app_id}").json()
    assert detail["current_stage"] == "Hired"

    history = http.get(f"/applications/{app_id}/history").json()
    assert [h["stage"] for h in history] == [
        "New", "Phone screen scheduled", "Interview scheduled", "Hired",
    ]
    assert [n["content"] for n in history[0]["notes"]] == ["Strong resume"]
    assert [n["content"] for n in history[1]["notes"]] == ["Call on Monday"]
    assert history[2]["notes"] == [] and history[3]["notes"] == []
    entered = [h["entered_at"] for h in history]
    assert entered == sorted(entered)

    # final stage cannot change
    assert http.put(f"/applications/{app_id}/stage", json={"stage": "Rejected"}).status_code == 409


def test_create_and_fetch(http, new_application):
    app = new_application()
    assert app["receipt"].startswith("thank-you-from-b12-")
    res = http.get(f"/applications/{app['id']}")
    assert res.status_code == 200 and res.json() == {k: v for k, v in app.items() if k != "success"}


def test_create_validation(http):
    assert http.post("/applications", json={"name": "X", "email": "bad"}).status_code == 422
    assert http.post("/applications", json={"name": " ", "email": "a@example.com"}).status_code == 422
    assert http.post("/applications", json={}).status_code == 422
    assert http.post("/applications", content=b"not json", headers={"content-type": "application/json"}).status_code == 422


def test_unknown_application_returns_404(http):
    assert http.get("/applications/99999999").status_code == 404
    assert http.get("/applications/99999999/history").status_code == 404
    assert http.put("/applications/99999999/stage", json={"stage": "Hired"}).status_code == 404
    assert http.post("/applications/99999999/notes", json={"content": "x"}).status_code == 404


def test_stage_rules_over_http(http, new_application):
    app_id = new_application()["id"]
    url = f"/applications/{app_id}/stage"
    assert http.put(url, json={"stage": "New"}).status_code == 409  # same stage
    assert http.put(url, json={"stage": "Interview scheduled"}).status_code == 200  # skip ahead
    assert http.put(url, json={"stage": "Phone screen scheduled"}).status_code == 409  # backwards
    assert http.put(url, json={"stage": "Banana"}).status_code == 422
    assert http.put(url, json={}).status_code == 422
    assert http.put(url, json={"stage": "Rejected"}).status_code == 200
    assert http.put(url, json={"stage": "Hired"}).status_code == 409  # final
    # failed attempts left no extra history
    assert [h["stage"] for h in http.get(f"/applications/{app_id}/history").json()] == [
        "New", "Interview scheduled", "Rejected",
    ]


def test_notes(http, new_application):
    app_id = new_application()["id"]
    url = f"/applications/{app_id}/notes"
    first = http.post(url, json={"content": "  one  "})
    assert first.status_code == 201 and first.json()["content"] == "one"
    http.post(url, json={"content": "two"})
    for bad in ({"content": ""}, {"content": "   "}, {}):
        assert http.post(url, json=bad).status_code == 422
    notes = http.get(f"/applications/{app_id}/history").json()[0]["notes"]
    assert [n["content"] for n in notes] == ["one", "two"]
    assert {n["stage_id"] for n in notes} == {first.json()["stage_id"]}


def test_list_filters_and_shape(http, new_application):
    email = f"{uuid.uuid4().hex[:10]}@example.com"
    target = new_application(email=email.upper())  # email filter is case-insensitive
    new_application()

    res = http.get("/applications", params={"email": email}).json()
    assert res["total"] == 1
    item = res["items"][0]
    assert set(item) == {"id", "name", "email", "timestamp", "receipt"}
    assert item["id"] == target["id"]

    by_receipt = http.get("/applications", params={"receipt": target["receipt"]}).json()
    assert [i["id"] for i in by_receipt["items"]] == [target["id"]]
    assert http.get("/applications", params={"receipt": "nope"}).json()["total"] == 0

    both = http.get("/applications", params={"email": "someone-else@example.com", "receipt": target["receipt"]})
    assert both.json()["total"] == 0


def test_list_date_filters(http, new_application):
    app = new_application()
    day = app["timestamp"][:10]
    params = {"submitted_from": day, "submitted_to": day, "receipt": app["receipt"]}
    assert http.get("/applications", params=params).json()["total"] == 1
    assert http.get("/applications", params={"submitted_to": "2000-01-01", "receipt": app["receipt"]}).json()["total"] == 0
    assert http.get("/applications", params={"submitted_from": "2999-01-01"}).json()["total"] == 0
    assert http.get("/applications", params={"submitted_from": "2026-02-01", "submitted_to": "2026-01-01"}).status_code == 422
    assert http.get("/applications", params={"submitted_from": "not-a-date"}).status_code == 422


def test_list_pagination(http, new_application):
    for _ in range(3):
        new_application()
    page1 = http.get("/applications", params={"page": 1, "page_size": 2}).json()
    assert len(page1["items"]) == 2 and page1["total"] >= 3
    assert page1["page"] == 1 and page1["page_size"] == 2
    ids = [i["id"] for i in page1["items"]]
    assert ids == sorted(ids, reverse=True)  # newest first
    page2 = http.get("/applications", params={"page": 2, "page_size": 2}).json()
    assert not set(ids) & {i["id"] for i in page2["items"]}
    assert http.get("/applications", params={"page": 10**6}).json()["items"] == []
    for bad in ({"page": 0}, {"page_size": 0}, {"page_size": 101}, {"page": "x"}):
        assert http.get("/applications", params=bad).status_code == 422


def test_applications_are_isolated(http, new_application):
    a, b = new_application(), new_application()
    http.post(f"/applications/{a['id']}/notes", json={"content": "only a"})
    http.put(f"/applications/{a['id']}/stage", json={"stage": "Rejected"})
    assert http.get(f"/applications/{b['id']}").json()["current_stage"] == "New"
    hist_b = http.get(f"/applications/{b['id']}/history").json()
    assert len(hist_b) == 1 and hist_b[0]["notes"] == []
