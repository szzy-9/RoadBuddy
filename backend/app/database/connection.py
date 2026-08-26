from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
DB_CONNECT_TIMEOUT_SECONDS = 3
DB_POOL_TIMEOUT_SECONDS = 5
DB_STATEMENT_TIMEOUT_MILLISECONDS = 5_000

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_timeout=DB_POOL_TIMEOUT_SECONDS,
    connect_args={
        "connect_timeout": DB_CONNECT_TIMEOUT_SECONDS,
        "options": f"-c statement_timeout={DB_STATEMENT_TIMEOUT_MILLISECONDS}",
    },
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
