import os

# Harus diatur sebelum app diimpor, karena Settings dibaca saat import.
os.environ["INTERNAL_SECRET"] = "test-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def auth():
    return {"X-Internal-Secret": "test-secret"}
