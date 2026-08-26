from io import BytesIO

import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from etl.s3_source import (
    InvalidS3UriError,
    S3ConfigurationError,
    S3Location,
    S3ObjectNotFoundError,
    open_s3_object,
    parse_s3_uri,
)


class FakeS3Client:
    def __init__(self, *, body: BytesIO | None = None, error: Exception | None = None):
        self.body = body
        self.error = error
        self.requests: list[tuple[str, str]] = []

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        self.requests.append((Bucket, Key))
        if self.error is not None:
            raise self.error
        return {"Body": self.body}


@pytest.mark.parametrize(
    ("uri", "expected"),
    [
        (
            "s3://roadbuddy-data/crash/victoria-road-crash-data.csv",
            S3Location(
                bucket="roadbuddy-data",
                key="crash/victoria-road-crash-data.csv",
            ),
        ),
        (
            "s3://roadbuddy-data/speed-zones/victoria-speed-zones.geojson",
            S3Location(
                bucket="roadbuddy-data",
                key="speed-zones/victoria-speed-zones.geojson",
            ),
        ),
    ],
)
def test_parse_s3_uri(uri: str, expected: S3Location) -> None:
    assert parse_s3_uri(uri) == expected


@pytest.mark.parametrize(
    "uri",
    [
        "https://example.com/data.csv",
        "s3:///data.csv",
        "s3://roadbuddy-data",
        "s3://roadbuddy-data/data.csv?versionId=123",
        "s3://roadbuddy-data/data.csv#section",
    ],
)
def test_parse_s3_uri_rejects_invalid_sources(uri: str) -> None:
    with pytest.raises(InvalidS3UriError):
        parse_s3_uri(uri)


def test_open_s3_object_streams_and_closes_body() -> None:
    body = BytesIO(b"id,crash_type\n1,rear-end\n")
    client = FakeS3Client(body=body)
    uri = "s3://test-bucket/crash/sample.csv"

    with open_s3_object(uri, client=client) as stream:
        assert stream.read(2) == b"id"
        assert not body.closed

    assert body.closed
    assert client.requests == [("test-bucket", "crash/sample.csv")]


def test_open_s3_object_reports_missing_object() -> None:
    error = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "missing"}},
        "GetObject",
    )

    with pytest.raises(S3ObjectNotFoundError, match="was not found"):
        with open_s3_object(
            "s3://test-bucket/missing.csv",
            client=FakeS3Client(error=error),
        ):
            pass


def test_open_s3_object_reports_credential_failure() -> None:
    with pytest.raises(S3ConfigurationError, match="credentials or configuration"):
        with open_s3_object(
            "s3://test-bucket/crash/sample.csv",
            client=FakeS3Client(error=NoCredentialsError()),
        ):
            pass
