"""E2E fixtures: run the real app under uvicorn against a throwaway SQLite file
and talk to it over HTTP, exercising startup (table creation) and the full stack."""
import os
import socket
import subprocess
import sys
import time
import uuid

import httpx
import pytest


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def base_url(tmp_path_factory):
    port = _free_port()
    db_file = tmp_path_factory.mktemp("e2e") / "e2e.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_file}"}
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.time() + 15
        while time.time() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(f"server exited early:\n{proc.stdout.read().decode()}")
            try:
                httpx.get(f"{url}/openapi.json", timeout=1).raise_for_status()
                break
            except httpx.HTTPError:
                time.sleep(0.1)
        else:
            raise RuntimeError("server did not start in time")
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture
def http(base_url):
    with httpx.Client(base_url=base_url, timeout=5) as c:
        yield c


@pytest.fixture
def new_application(http):
    """Create an application with a unique email so tests never collide."""

    def _make(name="Ada Lovelace", email=None):
        email = email or f"{uuid.uuid4().hex[:10]}@example.com"
        res = http.post("/applications", json={"name": name, "email": email})
        assert res.status_code == 201, res.text
        return res.json()

    return _make
