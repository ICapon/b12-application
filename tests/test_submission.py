"""POST /applications as called by submit.py: signed payload using the script's own helpers."""
import pytest

import submit

KEY = "test-signing-key"
ENV = {
    "GITHUB_SERVER_URL": "https://github.com",
    "GITHUB_REPOSITORY": "someone/b12-application",
    "GITHUB_RUN_ID": "42",
    "APPLICANT_NAME": "Ada Lovelace",
    "APPLICANT_EMAIL": "ada@example.com",
    "RESUME_LINK": "https://example.com/resume",
}


@pytest.fixture(autouse=True)
def signing_key(monkeypatch):
    monkeypatch.setenv("SIGNING_KEY", KEY)
    monkeypatch.delenv("REQUIRE_SIGNATURE", raising=False)


def post_signed(client, body=None, signature=None):
    body = body if body is not None else submit.build_body(submit.build_payload(ENV))
    signature = signature or submit.sign(body, KEY.encode())
    return client.post(
        "/applications",
        content=body,
        headers={"Content-Type": "application/json", "X-Signature-256": signature},
    )


def test_script_payload_is_accepted_and_stored(client):
    res = post_signed(client)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["success"] is True and data["receipt"]
    assert data["name"] == "Ada Lovelace" and data["email"] == "ada@example.com"
    assert data["resume_link"] == "https://example.com/resume"
    assert data["repository_link"] == "https://github.com/someone/b12-application"
    assert data["action_run_link"] == "https://github.com/someone/b12-application/actions/runs/42"
    assert client.get(f"/applications/{data['id']}").json()["resume_link"] == data["resume_link"]


def test_client_timestamp_is_stored(client):
    body = submit.build_body({**submit.build_payload(ENV), "timestamp": "2026-03-04T05:06:07.890Z"})
    res = post_signed(client, body)
    assert res.json()["timestamp"].startswith("2026-03-04T05:06:07.890")


def test_bad_signature_is_rejected(client):
    assert post_signed(client, signature="sha256=" + "0" * 64).status_code == 401


def test_tampered_body_is_rejected(client):
    body = submit.build_body(submit.build_payload(ENV))
    signature = submit.sign(body, KEY.encode())
    assert post_signed(client, body.replace(b"Ada", b"Eve"), signature).status_code == 401


def test_wrong_key_is_rejected(client):
    body = submit.build_body(submit.build_payload(ENV))
    assert post_signed(client, body, submit.sign(body, b"other")).status_code == 401


def test_signed_request_without_server_key_is_500(client, monkeypatch):
    monkeypatch.delenv("SIGNING_KEY")
    assert post_signed(client).status_code == 500


def test_unsigned_allowed_by_default_but_enforceable(client, monkeypatch):
    body = {"name": "A", "email": "a@example.com"}
    assert client.post("/applications", json=body).status_code == 201
    monkeypatch.setenv("REQUIRE_SIGNATURE", "1")
    assert client.post("/applications", json=body).status_code == 401


def test_unknown_field_is_rejected(client):
    body = submit.build_body({**submit.build_payload(ENV), "extra": "x"})
    assert post_signed(client, body).status_code == 422
