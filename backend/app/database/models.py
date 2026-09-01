from datetime import date, datetime, time

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Double,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class SourceMetadata(Base):
    __tablename__ = "source_metadata"

    source_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    licence: Mapped[str | None] = mapped_column(String(80))
    notes: Mapped[str | None] = mapped_column(Text)


class DatasetSnapshot(Base):
    __tablename__ = "dataset_snapshot"

    snapshot_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_metadata.source_id")
    )
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime)
    coverage_start: Mapped[date | None] = mapped_column(Date)
    coverage_end: Mapped[date | None] = mapped_column(Date)
    s3_object_key: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128))
    row_count: Mapped[int | None] = mapped_column(Integer)
    validation_status: Mapped[str | None] = mapped_column(String(40))


class Crash(Base):
    __tablename__ = "crash"

    accident_no: Mapped[str] = mapped_column(String(30), primary_key=True)
    accident_date: Mapped[date] = mapped_column(Date, nullable=False)
    accident_time: Mapped[time | None] = mapped_column(Time)

    accident_type: Mapped[str | None] = mapped_column(String(120))
    day_of_week: Mapped[str | None] = mapped_column(String(20))
    dca_code: Mapped[str | None] = mapped_column(String(20))
    dca_code_description: Mapped[str | None] = mapped_column(Text)
    light_condition: Mapped[str | None] = mapped_column(String(100))
    police_attend: Mapped[str | None] = mapped_column(String(80))
    road_geometry: Mapped[str | None] = mapped_column(String(100))
    severity: Mapped[str | None] = mapped_column(String(80))

    speed_zone_raw: Mapped[str | None] = mapped_column(String(50))
    speed_zone_kmh: Mapped[int | None] = mapped_column(Integer)
    speed_zone_known: Mapped[bool | None] = mapped_column(Boolean)

    run_offroad: Mapped[str | None] = mapped_column(String(40))
    road_name: Mapped[str | None] = mapped_column(String(160))
    road_type: Mapped[str | None] = mapped_column(String(80))
    lga_name: Mapped[str | None] = mapped_column(String(120))
    dtp_region: Mapped[str | None] = mapped_column(String(120))

    latitude: Mapped[float | None] = mapped_column(Double)
    longitude: Mapped[float | None] = mapped_column(Double)
    vicgrid_x: Mapped[float | None] = mapped_column(Double)
    vicgrid_y: Mapped[float | None] = mapped_column(Double)

    total_persons: Mapped[int | None] = mapped_column(Integer)
    inj_or_fatal: Mapped[int | None] = mapped_column(Integer)
    fatality: Mapped[int | None] = mapped_column(Integer)
    serious_injury: Mapped[int | None] = mapped_column(Integer)
    other_injury: Mapped[int | None] = mapped_column(Integer)
    non_injured: Mapped[int | None] = mapped_column(Integer)

    males: Mapped[int | None] = mapped_column(Integer)
    females: Mapped[int | None] = mapped_column(Integer)
    bicyclist: Mapped[int | None] = mapped_column(Integer)
    passenger: Mapped[int | None] = mapped_column(Integer)
    driver: Mapped[int | None] = mapped_column(Integer)
    pedestrian: Mapped[int | None] = mapped_column(Integer)
    pillion: Mapped[int | None] = mapped_column(Integer)
    motorcyclist: Mapped[int | None] = mapped_column(Integer)
    unknown: Mapped[int | None] = mapped_column(Integer)

    ped_cyclist_5_12: Mapped[int | None] = mapped_column(Integer)
    ped_cyclist_13_18: Mapped[int | None] = mapped_column(Integer)
    old_ped_65_and_over: Mapped[int | None] = mapped_column(Integer)
    old_driver_75_and_over: Mapped[int | None] = mapped_column(Integer)
    young_driver_18_25: Mapped[int | None] = mapped_column(Integer)

    no_of_vehicles: Mapped[int | None] = mapped_column(Integer)
    heavy_vehicle: Mapped[int | None] = mapped_column(Integer)
    passenger_vehicle: Mapped[int | None] = mapped_column(Integer)
    pt_vehicle: Mapped[int | None] = mapped_column(Integer)

    deg_urban_name: Mapped[str | None] = mapped_column(String(120))
    rma: Mapped[str | None] = mapped_column(String(120))

    hour: Mapped[int | None] = mapped_column(SmallInteger)
    time_band: Mapped[str | None] = mapped_column(String(40))
    overnight: Mapped[bool | None] = mapped_column(Boolean)

    has_known_surface: Mapped[bool | None] = mapped_column(Boolean)
    has_wet_surface: Mapped[bool | None] = mapped_column(Boolean)
    has_known_atmosphere: Mapped[bool | None] = mapped_column(Boolean)
    has_raining_condition: Mapped[bool | None] = mapped_column(Boolean)
    has_young_driver_16_25: Mapped[bool | None] = mapped_column(Boolean)

    geom: Mapped[object | None] = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=True)
    )


class CrashPerson(Base):
    __tablename__ = "crash_person"

    accident_no: Mapped[str] = mapped_column(
        ForeignKey("crash.accident_no", ondelete="CASCADE"),
        primary_key=True,
    )
    person_id: Mapped[str] = mapped_column(String(30), primary_key=True)

    age_group_raw: Mapped[str | None] = mapped_column(String(40))
    age_group_norm: Mapped[str | None] = mapped_column(String(40))
    road_user_type: Mapped[str | None] = mapped_column(String(40))
    road_user_type_desc: Mapped[str | None] = mapped_column(String(80))

    is_driver: Mapped[bool | None] = mapped_column(Boolean)
    is_young_driver_16_25: Mapped[bool | None] = mapped_column(Boolean)


class CrashSurfaceCondition(Base):
    __tablename__ = "crash_surface_condition"

    accident_no: Mapped[str] = mapped_column(
        ForeignKey("crash.accident_no", ondelete="CASCADE"),
        primary_key=True,
    )
    surface_cond: Mapped[str | None] = mapped_column(String(20))
    surface_cond_desc: Mapped[str | None] = mapped_column(String(80))
    surface_cond_seq: Mapped[int] = mapped_column(Integer, primary_key=True)


class CrashAtmosphericCondition(Base):
    __tablename__ = "crash_atmospheric_condition"

    accident_no: Mapped[str] = mapped_column(
        ForeignKey("crash.accident_no", ondelete="CASCADE"),
        primary_key=True,
    )
    atmosph_cond: Mapped[str | None] = mapped_column(String(20))
    atmosph_cond_desc: Mapped[str | None] = mapped_column(String(80))
    atmosph_cond_seq: Mapped[int] = mapped_column(Integer, primary_key=True)


class CrashCluster200m(Base):
    __tablename__ = "crash_cluster_200m"

    cluster_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    grid_x: Mapped[float] = mapped_column(Double, nullable=False)
    grid_y: Mapped[float] = mapped_column(Double, nullable=False)

    total_crashes: Mapped[int] = mapped_column(Integer, nullable=False)
    eligible_driver_age_crashes: Mapped[int] = mapped_column(Integer, nullable=False)
    young_driver_crashes: Mapped[int] = mapped_column(Integer, nullable=False)

    young_driver_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    young_driver_pct_displayable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    geom: Mapped[object] = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=True),
        nullable=False,
    )

