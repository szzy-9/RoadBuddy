from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class CrashRecord(Base):
    __tablename__ = "crash_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crash_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    crash_type: Mapped[str] = mapped_column(String(120), nullable=False)
    road_condition: Mapped[str | None] = mapped_column(String(80))
    light_condition: Mapped[str | None] = mapped_column(String(80))
    severity: Mapped[str | None] = mapped_column(String(80))
    geometry: Mapped[object] = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=True),
        nullable=False,
    )


class CrashCluster(Base):
    __tablename__ = "crash_clusters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(180))
    crash_count: Mapped[int] = mapped_column(Integer, nullable=False)
    dominant_type: Mapped[str | None] = mapped_column(String(120))
    wet_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dark_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    geometry: Mapped[object] = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=True),
        nullable=False,
    )


class SpeedZone(Base):
    __tablename__ = "speed_zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    speed_limit: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    geometry: Mapped[object] = mapped_column(
        Geometry("MULTILINESTRING", srid=4326, spatial_index=True),
        nullable=False,
    )


class DatasetMetadata(Base):
    __tablename__ = "dataset_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    licence: Mapped[str] = mapped_column(Text, nullable=False)
