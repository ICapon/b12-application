def test_empty_list(client):
    assert client.get("/applications").json() == {
        "items": [], "total": 0, "page": 1, "page_size": 20,
    }


def test_list_items_only_have_summary_fields(client, make_application):
    make_application()
    item = client.get("/applications").json()["items"][0]
    assert set(item) == {"id", "name", "email", "timestamp", "receipt"}


def test_pagination(client, make_application):
    ids = [make_application(email=f"u{i}@example.com")["id"] for i in range(5)]
    first = client.get("/applications?page=1&page_size=2").json()
    last = client.get("/applications?page=3&page_size=2").json()
    beyond = client.get("/applications?page=4&page_size=2").json()
    assert first["total"] == 5
    assert [i["id"] for i in first["items"]] == [ids[4], ids[3]]  # newest first
    assert [i["id"] for i in last["items"]] == [ids[0]]
    assert beyond["items"] == []


def test_invalid_pagination_params(client):
    for qs in ["page=0", "page_size=0", "page_size=101", "page=x"]:
        assert client.get(f"/applications?{qs}").status_code == 422


def test_filter_by_email_is_case_insensitive(client, make_application):
    make_application(email="ada@example.com")
    make_application(email="bob@example.com")
    res = client.get("/applications?email=ADA@example.com").json()
    assert res["total"] == 1
    assert res["items"][0]["email"] == "ada@example.com"


def test_filter_by_receipt(client, make_application):
    target = make_application()
    make_application(email="other@example.com")
    res = client.get(f"/applications?receipt={target['receipt']}").json()
    assert [i["id"] for i in res["items"]] == [target["id"]]
    assert client.get("/applications?receipt=nope").json()["total"] == 0


def test_filter_by_date_is_inclusive_whole_day(client, make_application):
    app = make_application()
    day = app["timestamp"][:10]
    assert client.get(f"/applications?submitted_from={day}&submitted_to={day}").json()["total"] == 1
    assert client.get("/applications?submitted_to=2000-01-01").json()["total"] == 0
    assert client.get("/applications?submitted_from=2999-01-01").json()["total"] == 0


def test_date_range_reversed_is_422(client):
    res = client.get("/applications?submitted_from=2026-02-01&submitted_to=2026-01-01")
    assert res.status_code == 422


def test_combined_filters_are_anded(client, make_application):
    a = make_application(email="ada@example.com")
    make_application(email="bob@example.com")
    res = client.get(f"/applications?email=bob@example.com&receipt={a['receipt']}").json()
    assert res["total"] == 0
