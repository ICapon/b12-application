def set_stage(client, app_id, stage):
    return client.put(f"/applications/{app_id}/stage", json={"stage": stage})


def test_move_forward(client, make_application):
    app = make_application()
    res = set_stage(client, app["id"], "Phone screen scheduled")
    assert res.status_code == 200
    assert res.json()["current_stage"] == "Phone screen scheduled"
    assert client.get(f"/applications/{app['id']}").json()["current_stage"] == "Phone screen scheduled"


def test_backward_and_same_stage_rejected(client, make_application):
    app = make_application()
    set_stage(client, app["id"], "Interview scheduled")
    assert set_stage(client, app["id"], "New").status_code == 409
    assert set_stage(client, app["id"], "Interview scheduled").status_code == 409


def test_terminal_stage_is_final(client, make_application):
    app = make_application()
    assert set_stage(client, app["id"], "Rejected").status_code == 200
    assert set_stage(client, app["id"], "Hired").status_code == 409


def test_invalid_stage_name_is_422(client, make_application):
    app = make_application()
    assert set_stage(client, app["id"], "Banana").status_code == 422
    assert client.put(f"/applications/{app['id']}/stage", json={}).status_code == 422


def test_failed_move_does_not_add_history(client, make_application):
    app = make_application()
    set_stage(client, app["id"], "New")
    assert len(client.get(f"/applications/{app['id']}/history").json()) == 1


def test_create_note_attaches_to_current_stage(client, make_application):
    app = make_application()
    res = client.post(f"/applications/{app['id']}/notes", json={"content": "  Looks good  "})
    assert res.status_code == 201
    assert res.json()["content"] == "Looks good"  # stripped


def test_blank_note_rejected(client, make_application):
    app = make_application()
    for body in [{"content": ""}, {"content": "   "}, {}]:
        assert client.post(f"/applications/{app['id']}/notes", json=body).status_code == 422


def test_history_groups_notes_by_stage_in_order(client, make_application):
    app = make_application()
    n = lambda text: client.post(f"/applications/{app['id']}/notes", json={"content": text})
    n("first")
    n("second")
    set_stage(client, app["id"], "Phone screen scheduled")
    n("after move")

    history = client.get(f"/applications/{app['id']}/history").json()
    assert [h["stage"] for h in history] == ["New", "Phone screen scheduled"]
    assert [x["content"] for x in history[0]["notes"]] == ["first", "second"]
    assert [x["content"] for x in history[1]["notes"]] == ["after move"]
    assert all(h["entered_at"] for h in history)


def test_history_of_new_application(client, make_application):
    app = make_application()
    history = client.get(f"/applications/{app['id']}/history").json()
    assert len(history) == 1 and history[0]["stage"] == "New" and history[0]["notes"] == []


def test_applications_do_not_share_history(client, make_application):
    a = make_application()
    b = make_application(email="b@example.com")
    client.post(f"/applications/{a['id']}/notes", json={"content": "only a"})
    assert client.get(f"/applications/{b['id']}/history").json()[0]["notes"] == []
