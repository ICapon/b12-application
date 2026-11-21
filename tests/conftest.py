import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db, make_engine
from app.main import app


@pytest.fixture
def client():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)  # no `with`: skips lifespan, so the real DB is untouched
    app.dependency_overrides.clear()


@pytest.fixture
def make_application(client):
    def _make(name="Ada Lovelace", email="ada@example.com"):
        res = client.post("/applications", json={"name": name, "email": email})
        assert res.status_code == 201, res.text
        return res.json()

    return _make
