import os

import pytest
from fastapi.testclient import TestClient

os.environ["USE_MOCK_DATA"] = "true"

from app.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402

get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client

