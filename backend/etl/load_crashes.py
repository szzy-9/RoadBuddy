"""Load Victorian road crash datasets into RoadBuddy PostgreSQL/PostGIS.

This loader:
- preserves every crash, person, surface-condition and atmospheric-condition row
- derives crash-level RoadBuddy flags from the detailed source tables
- keeps unknown values distinct from known conditions
- creates geometry only for valid Victorian coordinates
- does not infer speed limits or missing conditions

Run from the backend directory:
    python -m etl.load_crashes
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from app.database.connection import engine


DATA_DIR = Path(__file__).resolve().parents[1] / "data"

CRASH_FILE = DATA_DIR / "victorian_road_crash_data.csv"
PERSON_FILE = DATA_DIR / "person.csv"
SURFACE_FILE = DATA_DIR / "road_surface_cond.csv"
ATMOSPHERE_FILE = DATA_DIR / "atmospheric_cond.csv"

YOUNG_AGE_GROUPS = {"16-17", "18-21", "22-25"}

EXPECTED_COUNTS = {
    "crash": 200_352,
    "person": 467_730,
    "surface": 201_426,
    "atmosphere": 202_905,
}

INTEGER_COLUMNS = [
    "TOTAL_PERSONS",
    "INJ_OR_FATAL",
    "FATALITY",
    "SERIOUSINJURY",
    "OTHERINJURY",
    "NONINJURED",
    "MALES",
    "FEMALES",
    "BICYCLIST",
    "PASSENGER",
    "DRIVER",
    "PEDESTRIAN",
    "PILLION",
    "MOTORCYCLIST",
    "UNKNOWN",
    "PED_CYCLIST_5_12",
    "PED_CYCLIST_13_18",
    "OLD_PED_65_AND_OVER",
    "OLD_DRIVER_75_AND_OVER",
    "YOUNG_DRIVER_18_25",
    "NO_OF_VEHICLES",
    "HEAVYVEHICLE",
    "PASSENGERVEHICLE",
    "PT_VEHICLE",
]


def normalize_age_group(value: object) -> str | None:
    """Normalize source age-band punctuation without inventing an age."""
    if pd.isna(value):
        return None

    normalized = str(value).strip().replace("–", "-").replace("—", "-")
    return normalized or None


def read_sources() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    print("Reading local source CSVs...")

    crash = pd.read_csv(CRASH_FILE, low_memory=False)
    person = pd.read_csv(PERSON_FILE, low_memory=False)
    surface = pd.read_csv(SURFACE_FILE, low_memory=False)
    atmosphere = pd.read_csv(ATMOSPHERE_FILE, low_memory=False)

    print(f"  crash:      {len(crash):,}")
    print(f"  person:     {len(person):,}")
    print(f"  surface:    {len(surface):,}")
    print(f"  atmosphere: {len(atmosphere):,}")

    return crash, person, surface, atmosphere


def validate_source_counts(
    crash: pd.DataFrame,
    person: pd.DataFrame,
    surface: pd.DataFrame,
    atmosphere: pd.DataFrame,
) -> None:
    actual = {
        "crash": len(crash),
        "person": len(person),
        "surface": len(surface),
        "atmosphere": len(atmosphere),
    }

    for name, expected in EXPECTED_COUNTS.items():
        if actual[name] != expected:
            raise ValueError(
                f"{name} row count mismatch: "
                f"expected {expected:,}, got {actual[name]:,}"
            )

    if crash["ACCIDENT_NO"].duplicated().any():
        raise ValueError("Duplicate ACCIDENT_NO found in crash source")

    if person.duplicated(["ACCIDENT_NO", "PERSON_ID"]).any():
        raise ValueError("Duplicate (ACCIDENT_NO, PERSON_ID) found")

    if surface.duplicated(["ACCIDENT_NO", "SURFACE_COND_SEQ"]).any():
        raise ValueError("Duplicate surface-condition primary key found")

    if atmosphere.duplicated(["ACCIDENT_NO", "ATMOSPH_COND_SEQ"]).any():
        raise ValueError("Duplicate atmospheric-condition primary key found")

    print("Source counts and primary keys OK.")


def prepare_person(person: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    result = person[
        [
            "ACCIDENT_NO",
            "PERSON_ID",
            "AGE_GROUP",
            "ROAD_USER_TYPE",
            "ROAD_USER_TYPE_DESC",
        ]
    ].copy()

    result["age_group_norm"] = result["AGE_GROUP"].map(normalize_age_group)

    result["is_driver"] = (
        result["ROAD_USER_TYPE_DESC"].astype("string").str.strip().eq("Drivers")
    )

    result["is_young_driver_16_25"] = (
        result["is_driver"]
        & result["age_group_norm"].isin(YOUNG_AGE_GROUPS)
    )

    crash_young = (
        result.groupby("ACCIDENT_NO")["is_young_driver_16_25"]
        .max()
        .astype(bool)
    )

    result = result.rename(
        columns={
            "ACCIDENT_NO": "accident_no",
            "PERSON_ID": "person_id",
            "AGE_GROUP": "age_group_raw",
            "ROAD_USER_TYPE": "road_user_type",
            "ROAD_USER_TYPE_DESC": "road_user_type_desc",
        }
    )

    return result, crash_young


def prepare_surface(surface: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    working = surface.copy()

    desc = working["SURFACE_COND_DESC"].astype("string").str.strip()

    working["_known"] = desc.notna() & desc.ne("Unk.")
    working["_wet"] = desc.eq("Wet").fillna(False)

    flags = working.groupby("ACCIDENT_NO").agg(
        has_known_surface=("_known", "max"),
        has_wet_surface=("_wet", "max"),
    )

    result = working[
        [
            "ACCIDENT_NO",
            "SURFACE_COND",
            "SURFACE_COND_DESC",
            "SURFACE_COND_SEQ",
        ]
    ].rename(
        columns={
            "ACCIDENT_NO": "accident_no",
            "SURFACE_COND": "surface_cond",
            "SURFACE_COND_DESC": "surface_cond_desc",
            "SURFACE_COND_SEQ": "surface_cond_seq",
        }
    )

    return result, flags


def prepare_atmosphere(
    atmosphere: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    working = atmosphere.copy()

    desc = working["ATMOSPH_COND_DESC"].astype("string").str.strip()

    working["_known"] = desc.notna() & desc.ne("Not known")
    working["_raining"] = desc.eq("Raining").fillna(False)

    flags = working.groupby("ACCIDENT_NO").agg(
        has_known_atmosphere=("_known", "max"),
        has_raining_condition=("_raining", "max"),
    )

    result = working[
        [
            "ACCIDENT_NO",
            "ATMOSPH_COND",
            "ATMOSPH_COND_DESC",
            "ATMOSPH_COND_SEQ",
        ]
    ].rename(
        columns={
            "ACCIDENT_NO": "accident_no",
            "ATMOSPH_COND": "atmosph_cond",
            "ATMOSPH_COND_DESC": "atmosph_cond_desc",
            "ATMOSPH_COND_SEQ": "atmosph_cond_seq",
        }
    )

    return result, flags


def prepare_crash(
    crash: pd.DataFrame,
    young_flags: pd.Series,
    surface_flags: pd.DataFrame,
    atmosphere_flags: pd.DataFrame,
) -> pd.DataFrame:
    result = crash.copy()

    # Dates are expected to be ISO YYYY-MM-DD.
    result["ACCIDENT_DATE"] = pd.to_datetime(
        result["ACCIDENT_DATE"],
        format="%Y-%m-%d",
        errors="raise",
    ).dt.date

    # Source contains both HH:MM:SS and fractional-second values such as
    # HH:MM:SS.0000000. Parse as a time duration so both forms are retained.
    parsed_time = pd.to_timedelta(
        result["ACCIDENT_TIME"].astype("string").str.strip(),
        errors="coerce",
    )

    result["hour"] = parsed_time.dt.components["hours"].astype("Int64")

    result["overnight"] = (
        (result["hour"] >= 22) | (result["hour"] < 6)
    ).astype("boolean")
    result.loc[result["hour"].isna(), "overnight"] = pd.NA

    def time_band(hour: object) -> str | None:
        if pd.isna(hour):
            return None

        hour = int(hour)

        if hour >= 22 or hour < 6:
            return "Overnight (10pm-6am)"
        if hour < 10:
            return "Morning (6am-10am)"
        if hour < 16:
            return "Daytime (10am-4pm)"
        if hour < 19:
            return "Evening peak (4pm-7pm)"
        return "Evening (7pm-10pm)"

    result["time_band"] = result["hour"].map(time_band)

    # PostgreSQL TIME receives Python time objects. Convert the parsed
    # duration back to a clock time while retaining valid fractional-second
    # source values.
    result["ACCIDENT_TIME"] = parsed_time.map(
        lambda value: (
            None
            if pd.isna(value)
            else (pd.Timestamp("1970-01-01") + value).time()
        )
    )

    # Preserve the original speed-zone value and only accept genuinely numeric
    # source values as numeric speed limits.
    result["speed_zone_raw"] = result["SPEED_ZONE"].astype("string")

    speed_text = result["SPEED_ZONE"].astype("string").str.strip()
    numeric_mask = speed_text.str.fullmatch(r"\d+").fillna(False)

    result["speed_zone_kmh"] = pd.Series(
        pd.NA,
        index=result.index,
        dtype="Int64",
    )
    result.loc[numeric_mask, "speed_zone_kmh"] = pd.to_numeric(
        speed_text[numeric_mask],
        errors="coerce",
    ).astype("Int64")

    result["speed_zone_known"] = numeric_mask.astype(bool)

    # Numeric coordinates remain raw columns even if geometry is invalid.
    result["LATITUDE"] = pd.to_numeric(result["LATITUDE"], errors="coerce")
    result["LONGITUDE"] = pd.to_numeric(result["LONGITUDE"], errors="coerce")

    # Conservative Victoria bounds. Invalid coordinates remain in the crash
    # table but receive NULL geometry.
    valid_geometry = (
        result["LATITUDE"].between(-39.3, -33.8)
        & result["LONGITUDE"].between(140.9, 150.1)
    )

    result["geom_wkt"] = None
    result.loc[valid_geometry, "geom_wkt"] = (
        "SRID=4326;POINT("
        + result.loc[valid_geometry, "LONGITUDE"].astype(str)
        + " "
        + result.loc[valid_geometry, "LATITUDE"].astype(str)
        + ")"
    )

    print(
        "Geometry: "
        f"{int(valid_geometry.sum()):,} valid, "
        f"{int((~valid_geometry).sum()):,} invalid/null"
    )

    result = result.set_index("ACCIDENT_NO")

    result = result.join(surface_flags, how="left")
    result = result.join(atmosphere_flags, how="left")
    result = result.join(
        young_flags.rename("has_young_driver_16_25"),
        how="left",
    )

    for column in [
        "has_known_surface",
        "has_wet_surface",
        "has_known_atmosphere",
        "has_raining_condition",
        "has_young_driver_16_25",
    ]:
        result[column] = result[column].fillna(False).astype(bool)

    result = result.reset_index()

    for column in INTEGER_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce").astype("Int64")

    result["VICGRID_X"] = pd.to_numeric(result["VICGRID_X"], errors="coerce")
    result["VICGRID_Y"] = pd.to_numeric(result["VICGRID_Y"], errors="coerce")

    rename = {
        "ACCIDENT_NO": "accident_no",
        "ACCIDENT_DATE": "accident_date",
        "ACCIDENT_TIME": "accident_time",
        "ACCIDENT_TYPE": "accident_type",
        "DAY_OF_WEEK": "day_of_week",
        "DCA_CODE": "dca_code",
        "DCA_CODE_DESCRIPTION": "dca_code_description",
        "LIGHT_CONDITION": "light_condition",
        "POLICE_ATTEND": "police_attend",
        "ROAD_GEOMETRY": "road_geometry",
        "SEVERITY": "severity",
        "RUN_OFFROAD": "run_offroad",
        "ROAD_NAME": "road_name",
        "ROAD_TYPE": "road_type",
        "LGA_NAME": "lga_name",
        "DTP_REGION": "dtp_region",
        "LATITUDE": "latitude",
        "LONGITUDE": "longitude",
        "VICGRID_X": "vicgrid_x",
        "VICGRID_Y": "vicgrid_y",
        "TOTAL_PERSONS": "total_persons",
        "INJ_OR_FATAL": "inj_or_fatal",
        "FATALITY": "fatality",
        "SERIOUSINJURY": "serious_injury",
        "OTHERINJURY": "other_injury",
        "NONINJURED": "non_injured",
        "MALES": "males",
        "FEMALES": "females",
        "BICYCLIST": "bicyclist",
        "PASSENGER": "passenger",
        "DRIVER": "driver",
        "PEDESTRIAN": "pedestrian",
        "PILLION": "pillion",
        "MOTORCYCLIST": "motorcyclist",
        "UNKNOWN": "unknown",
        "PED_CYCLIST_5_12": "ped_cyclist_5_12",
        "PED_CYCLIST_13_18": "ped_cyclist_13_18",
        "OLD_PED_65_AND_OVER": "old_ped_65_and_over",
        "OLD_DRIVER_75_AND_OVER": "old_driver_75_and_over",
        "YOUNG_DRIVER_18_25": "young_driver_18_25",
        "NO_OF_VEHICLES": "no_of_vehicles",
        "HEAVYVEHICLE": "heavy_vehicle",
        "PASSENGERVEHICLE": "passenger_vehicle",
        "PT_VEHICLE": "pt_vehicle",
        "DEG_URBAN_NAME": "deg_urban_name",
        "RMA": "rma",
    }

    result = result.rename(columns=rename)

    columns = [
        "accident_no",
        "accident_date",
        "accident_time",
        "accident_type",
        "day_of_week",
        "dca_code",
        "dca_code_description",
        "light_condition",
        "police_attend",
        "road_geometry",
        "severity",
        "speed_zone_raw",
        "speed_zone_kmh",
        "speed_zone_known",
        "run_offroad",
        "road_name",
        "road_type",
        "lga_name",
        "dtp_region",
        "latitude",
        "longitude",
        "vicgrid_x",
        "vicgrid_y",
        "total_persons",
        "inj_or_fatal",
        "fatality",
        "serious_injury",
        "other_injury",
        "non_injured",
        "males",
        "females",
        "bicyclist",
        "passenger",
        "driver",
        "pedestrian",
        "pillion",
        "motorcyclist",
        "unknown",
        "ped_cyclist_5_12",
        "ped_cyclist_13_18",
        "old_ped_65_and_over",
        "old_driver_75_and_over",
        "young_driver_18_25",
        "no_of_vehicles",
        "heavy_vehicle",
        "passenger_vehicle",
        "pt_vehicle",
        "deg_urban_name",
        "rma",
        "hour",
        "time_band",
        "overnight",
        "has_known_surface",
        "has_wet_surface",
        "has_known_atmosphere",
        "has_raining_condition",
        "has_young_driver_16_25",
        "geom_wkt",
    ]

    return result[columns]


def validate_transforms(
    crash: pd.DataFrame,
    person: pd.DataFrame,
    surface: pd.DataFrame,
    atmosphere: pd.DataFrame,
) -> None:
    print("\nTransformation validation:")

    print(f"  crash rows:      {len(crash):,}")
    print(f"  person rows:     {len(person):,}")
    print(f"  surface rows:    {len(surface):,}")
    print(f"  atmosphere rows: {len(atmosphere):,}")

    young_count = int(crash["has_young_driver_16_25"].sum())
    known_surface = int(crash["has_known_surface"].sum())
    wet = int(crash["has_wet_surface"].sum())
    known_atmosphere = int(crash["has_known_atmosphere"].sum())
    raining = int(crash["has_raining_condition"].sum())

    print(f"  young-driver crashes:       {young_count:,}")
    print(f"  known-surface crashes:      {known_surface:,}")
    print(f"  wet-surface crashes:        {wet:,}")
    print(f"  known-atmosphere crashes:   {known_atmosphere:,}")
    print(f"  raining-condition crashes:  {raining:,}")

    expected_flags = {
        "young-driver crashes": (young_count, 55_328),
        "known-surface crashes": (known_surface, 187_312),
        "wet-surface crashes": (wet, 28_940),
        "known-atmosphere crashes": (known_atmosphere, 179_570),
        "raining-condition crashes": (raining, 19_336),
    }

    for label, (actual, expected) in expected_flags.items():
        if actual != expected:
            raise ValueError(
                f"{label} mismatch: expected {expected:,}, got {actual:,}"
            )

    coverage_start = crash["accident_date"].min()
    coverage_end = crash["accident_date"].max()

    print(f"  coverage: {coverage_start} to {coverage_end}")

    if str(coverage_start) != "2012-01-01":
        raise ValueError(f"Unexpected coverage start: {coverage_start}")

    if str(coverage_end) != "2025-12-31":
        raise ValueError(f"Unexpected coverage end: {coverage_end}")

    print("Transformation validation OK.")


def insert_dataframe(
    connection,
    table_name: str,
    frame: pd.DataFrame,
    *,
    chunk_size: int = 5_000,
) -> None:
    """Insert a DataFrame using SQLAlchemy executemany in manageable chunks."""

    total = len(frame)

    for start in range(0, total, chunk_size):
        chunk = frame.iloc[start : start + chunk_size].copy()

        # Convert pandas missing values into Python None for psycopg.
        chunk = chunk.astype(object).where(pd.notna(chunk), None)

        records = chunk.to_dict(orient="records")
        columns = list(chunk.columns)

        if table_name == "crash":
            db_columns = [
                "geom" if column == "geom_wkt" else column
                for column in columns
            ]

            values = []
            for column in columns:
                if column == "geom_wkt":
                    values.append(
                        "ST_GeomFromEWKT(:geom_wkt)"
                    )
                else:
                    values.append(f":{column}")

            sql = text(
                f"""
                INSERT INTO {table_name}
                ({", ".join(db_columns)})
                VALUES ({", ".join(values)})
                """
            )
        else:
            placeholders = ", ".join(f":{column}" for column in columns)
            sql = text(
                f"""
                INSERT INTO {table_name}
                ({", ".join(columns)})
                VALUES ({placeholders})
                """
            )

        connection.execute(sql, records)

        done = min(start + chunk_size, total)
        print(f"    {table_name}: {done:,}/{total:,}")


def load_database(
    crash: pd.DataFrame,
    person: pd.DataFrame,
    surface: pd.DataFrame,
    atmosphere: pd.DataFrame,
) -> None:
    print("\nLoading database...")

    # One transaction: either the complete load succeeds or it rolls back.
    with engine.begin() as connection:
        # ETL operations can legitimately take longer than the API's normal
        # five-second request statement timeout.
        connection.execute(text("SET LOCAL statement_timeout = 0"))

        existing = connection.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM crash) AS crash_count,
                    (SELECT COUNT(*) FROM crash_person) AS person_count,
                    (SELECT COUNT(*) FROM crash_surface_condition) AS surface_count,
                    (SELECT COUNT(*) FROM crash_atmospheric_condition) AS atmosphere_count
                """
            )
        ).mappings().one()

        if any(int(value) > 0 for value in existing.values()):
            raise RuntimeError(
                "RoadBuddy crash tables are not empty. "
                "Loader stopped to avoid accidental duplicate/replacement data."
            )

        # Parent rows must exist before foreign-key child rows.
        insert_dataframe(connection, "crash", crash)
        insert_dataframe(connection, "crash_person", person)
        insert_dataframe(connection, "crash_surface_condition", surface)
        insert_dataframe(connection, "crash_atmospheric_condition", atmosphere)

    print("Database load committed.")


def validate_database() -> None:
    print("\nValidating database...")

    with engine.connect() as connection:
        counts = connection.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM crash) AS crash_count,
                    (SELECT COUNT(*) FROM crash_person) AS person_count,
                    (SELECT COUNT(*) FROM crash_surface_condition) AS surface_count,
                    (SELECT COUNT(*) FROM crash_atmospheric_condition) AS atmosphere_count
                """
            )
        ).mappings().one()

        print(f"  crash:      {counts['crash_count']:,}")
        print(f"  person:     {counts['person_count']:,}")
        print(f"  surface:    {counts['surface_count']:,}")
        print(f"  atmosphere: {counts['atmosphere_count']:,}")

        if counts["crash_count"] != EXPECTED_COUNTS["crash"]:
            raise ValueError("Database crash count failed validation")
        if counts["person_count"] != EXPECTED_COUNTS["person"]:
            raise ValueError("Database person count failed validation")
        if counts["surface_count"] != EXPECTED_COUNTS["surface"]:
            raise ValueError("Database surface count failed validation")
        if counts["atmosphere_count"] != EXPECTED_COUNTS["atmosphere"]:
            raise ValueError("Database atmosphere count failed validation")

        headline = connection.execute(
            text(
                """
                WITH crash_driver_age AS (
                    SELECT
                        c.accident_no,
                        c.overnight,
                        BOOL_OR(
                            cp.is_driver
                            AND cp.age_group_norm IS NOT NULL
                            AND cp.age_group_norm <> 'Unknown'
                        ) AS has_known_age_driver,
                        BOOL_OR(cp.is_young_driver_16_25) AS has_young_driver
                    FROM crash c
                    JOIN crash_person cp
                      ON cp.accident_no = c.accident_no
                    GROUP BY c.accident_no, c.overnight
                )
                SELECT
                    COUNT(*) FILTER (
                        WHERE has_known_age_driver
                    ) AS eligible_all,
                    COUNT(*) FILTER (
                        WHERE has_known_age_driver
                          AND has_young_driver
                    ) AS young_all,
                    COUNT(*) FILTER (
                        WHERE overnight IS TRUE
                          AND has_known_age_driver
                    ) AS eligible_overnight,
                    COUNT(*) FILTER (
                        WHERE overnight IS TRUE
                          AND has_known_age_driver
                          AND has_young_driver
                    ) AS young_overnight
                FROM crash_driver_age
                """
            )
        ).mappings().one()

        print(f"  eligible known-age driver crashes: {headline['eligible_all']:,}")
        print(f"  young-driver crashes:              {headline['young_all']:,}")
        print(f"  eligible overnight crashes:        {headline['eligible_overnight']:,}")
        print(f"  young overnight crashes:           {headline['young_overnight']:,}")

        expected_headline = {
            "eligible_all": 174_986,
            "young_all": 55_328,
            "eligible_overnight": 18_315,
            "young_overnight": 7_613,
        }

        for key, expected in expected_headline.items():
            if headline[key] != expected:
                raise ValueError(
                    f"Database headline validation failed for {key}: "
                    f"expected {expected:,}, got {headline[key]:,}"
                )

        pct_all = round(
            100 * headline["young_all"] / headline["eligible_all"],
            2,
        )
        pct_overnight = round(
            100
            * headline["young_overnight"]
            / headline["eligible_overnight"],
            2,
        )

        print(f"  young-driver share overall:   {pct_all:.2f}%")
        print(f"  young-driver share overnight: {pct_overnight:.2f}%")

        if pct_all != 31.62:
            raise ValueError(
                f"Expected overall young-driver share 31.62%, got {pct_all:.2f}%"
            )

        if pct_overnight != 41.57:
            raise ValueError(
                "Expected overnight young-driver share "
                f"41.57%, got {pct_overnight:.2f}%"
            )

    print("Database validation OK.")


def main() -> None:
    crash_raw, person_raw, surface_raw, atmosphere_raw = read_sources()

    validate_source_counts(
        crash_raw,
        person_raw,
        surface_raw,
        atmosphere_raw,
    )

    person, young_flags = prepare_person(person_raw)
    surface, surface_flags = prepare_surface(surface_raw)
    atmosphere, atmosphere_flags = prepare_atmosphere(atmosphere_raw)

    crash = prepare_crash(
        crash_raw,
        young_flags,
        surface_flags,
        atmosphere_flags,
    )

    validate_transforms(crash, person, surface, atmosphere)

    print(
        "\nPre-load validation passed. "
        "The next step would write these rows to PostgreSQL."
    )

    # Deliberately disabled until the transformation-only run is verified.
    load_database(crash, person, surface, atmosphere)
    validate_database()


if __name__ == "__main__":
    main()
