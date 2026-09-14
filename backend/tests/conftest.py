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


@pytest.fixture
def postgis_session():
    """Opt-in real PostGIS tests, using only transaction-local temporary tables.

    Set TEST_POSTGIS_URL to a PostgreSQL database with PostGIS installed.
    No permanent tables or data are created or modified.
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    database_url = os.environ.get("TEST_POSTGIS_URL")
    if not database_url:
        pytest.skip("Set TEST_POSTGIS_URL to run PostGIS integration tests")
    engine = create_engine(database_url, connect_args={"connect_timeout": 3})
    with engine.connect() as connection, connection.begin():
        connection.execute(text("""
            CREATE TEMP TABLE crash (
                accident_no text PRIMARY KEY, accident_date date,
                geom geometry(Point, 4326), road_name text, road_type text,
                dca_code_description text, has_wet_surface boolean,
                has_known_surface boolean, light_condition text
            ) ON COMMIT DROP
        """))
        connection.execute(text("""
            CREATE TEMP TABLE crash_cluster_200m (
                cluster_id bigint PRIMARY KEY, grid_x double precision,
                grid_y double precision, total_crashes integer,
                eligible_driver_age_crashes integer, young_driver_crashes integer,
                young_driver_pct numeric, young_driver_pct_displayable boolean,
                geom geometry(Point, 4326)
            ) ON COMMIT DROP
        """))
        with Session(bind=connection) as session:
            yield session
    engine.dispose()
