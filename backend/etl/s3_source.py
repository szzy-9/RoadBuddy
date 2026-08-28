from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import BinaryIO, Protocol, cast
from urllib.parse import urlsplit

import boto3
from botocore.exceptions import BotoCoreError, ClientError


class InvalidS3UriError(ValueError):
    """Raised when an ETL source URI is not a usable S3 object URI."""


class S3SourceError(RuntimeError):
    """Raised when an S3 object cannot be opened as an ETL source."""


class S3ObjectNotFoundError(S3SourceError):
    """Raised when the requested S3 bucket or object does not exist."""


class S3ConfigurationError(S3SourceError):
    """Raised when AWS credentials, permissions, or configuration are invalid."""


class S3Client(Protocol):
    def get_object(self, *, Bucket: str, Key: str) -> dict[str, object]: ...


@dataclass(frozen=True)
class S3Location:
    bucket: str
    key: str


def parse_s3_uri(uri: str) -> S3Location:
    value = uri.strip()
    parsed = urlsplit(value)

    if parsed.scheme.lower() != "s3":
        raise InvalidS3UriError("S3 source URI must start with s3://")
    if not parsed.netloc or any(character.isspace() for character in parsed.netloc):
        raise InvalidS3UriError("S3 source URI must include a bucket name")
    if parsed.query or parsed.fragment:
        raise InvalidS3UriError("S3 source URI must not include a query string or fragment")

    key = parsed.path.lstrip("/")
    if not key:
        raise InvalidS3UriError("S3 source URI must include an object key")

    return S3Location(bucket=parsed.netloc, key=key)


def _client_error_code(error: ClientError) -> str:
    return str(error.response.get("Error", {}).get("Code", "Unknown"))


@contextmanager
def open_s3_object(
    uri: str,
    *,
    client: S3Client | None = None,
) -> Iterator[BinaryIO]:
    """Open an S3 object as a streaming binary source without writing it locally."""

    location = parse_s3_uri(uri)

    try:
        s3_client = client or cast(S3Client, boto3.client("s3"))
        response = s3_client.get_object(Bucket=location.bucket, Key=location.key)
    except ClientError as exc:
        code = _client_error_code(exc)
        if code in {"404", "NoSuchBucket", "NoSuchKey", "NotFound"}:
            raise S3ObjectNotFoundError(f"S3 source object was not found: {uri}") from exc
        if code in {
            "AccessDenied",
            "ExpiredToken",
            "InvalidAccessKeyId",
            "SignatureDoesNotMatch",
        }:
            raise S3ConfigurationError(
                f"AWS credentials or permissions do not allow access to: {uri}"
            ) from exc
        raise S3SourceError(f"Could not access S3 source {uri} (AWS error {code})") from exc
    except BotoCoreError as exc:
        raise S3ConfigurationError(
            f"AWS credentials or configuration could not access: {uri}"
        ) from exc

    body = response.get("Body")
    if body is None or not callable(getattr(body, "read", None)):
        raise S3SourceError(f"S3 source did not return a readable object body: {uri}")

    stream = cast(BinaryIO, body)
    try:
        yield stream
    except BotoCoreError as exc:
        raise S3SourceError(f"S3 source stream failed while reading: {uri}") from exc
    finally:
        stream.close()
