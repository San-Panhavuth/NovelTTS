from collections.abc import Generator

from fastapi.testclient import TestClient

from app.main import app


def get_test_client() -> Generator[TestClient, None, None]:
    with TestClient(app) as client:
        yield client
