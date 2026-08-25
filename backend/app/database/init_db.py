from sqlalchemy import text

from app.database import models  # noqa: F401
from app.database.connection import Base, engine


def initialise_database() -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    initialise_database()

