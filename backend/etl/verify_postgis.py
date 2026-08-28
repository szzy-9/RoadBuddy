from collections.abc import Sequence

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.database.connection import engine
from app.database.models import CrashCluster, CrashRecord, DatasetMetadata, SpeedZone

EXPECTED_TABLES: Sequence[str] = (
    CrashRecord.__tablename__,
    CrashCluster.__tablename__,
    SpeedZone.__tablename__,
    DatasetMetadata.__tablename__,
)


def check_postgresql() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        print(f"[FAIL] PostgreSQL connectivity: {type(exc).__name__}")
        return False

    print("[OK] PostgreSQL connectivity")
    return True


def check_postgis() -> bool:
    try:
        with engine.connect() as connection:
            extension_version = connection.scalar(
                text("SELECT extversion FROM pg_extension WHERE extname = 'postgis'")
            )
            if extension_version is None:
                print("[FAIL] PostGIS is not enabled in this database")
                return False
            postgis_version = connection.scalar(text("SELECT PostGIS_Version()"))
    except SQLAlchemyError as exc:
        print(f"[FAIL] PostGIS check: {type(exc).__name__}")
        return False

    print(f"[OK] PostGIS available: {postgis_version}")
    return True


def check_expected_tables() -> bool:
    try:
        with engine.connect() as connection:
            existing_tables = set(inspect(connection).get_table_names(schema="public"))
    except SQLAlchemyError as exc:
        print(f"[FAIL] RoadBuddy table check: {type(exc).__name__}")
        return False

    missing_tables = [table for table in EXPECTED_TABLES if table not in existing_tables]
    for table in EXPECTED_TABLES:
        status = "OK" if table in existing_tables else "MISSING"
        print(f"[{status}] public.{table}")
    return not missing_tables


def main() -> int:
    if not check_postgresql():
        return 1

    postgis_ok = check_postgis()
    tables_ok = check_expected_tables()
    return 0 if postgis_ok and tables_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
