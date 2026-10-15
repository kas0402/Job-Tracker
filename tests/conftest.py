import os
from app import cache
os.environ["DATABASE_URL"] = (
    "postgresql+psycopg://jobtracker:jobtracker_pass@localhost:5432/jobtracker_test"
)
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    cache._client.flushdb()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    client.post("/register", json={"email": "a@example.com", "password": "password123"})
    resp = client.post("/login", data={"username": "a@example.com", "password": "password123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}