"""Order photos against an S3 bucket (simulated with moto), as in production (ADR-023)."""

from collections.abc import Iterator
from typing import Any

import boto3
import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient
from moto import mock_aws

from app.core.config import Settings
from app.core.storage import S3Storage

from .test_work_orders_api import (
    ORDERS,
    Setup,
    _create,
    _jpeg_with_gps,
    setup,  # noqa: F401 (fixture)
)

BUCKET = "erms-fotos-test"


@pytest.fixture
def s3() -> Iterator[Any]:
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        yield client


@pytest.fixture
def storage(s3: Any) -> S3Storage:
    """Overrides the local-disk fixture of conftest for this module."""
    settings = Settings(
        database_url="postgresql://u:p@h/db",
        s3_bucket=BUCKET,
        s3_endpoint="https://s3.amazonaws.com",
        s3_access_key_id="test-key",
        s3_secret_access_key="test-secret",
    )
    return S3Storage(settings, client=s3)


def _keys(s3: Any) -> list[str]:
    return [o["Key"] for o in s3.list_objects_v2(Bucket=BUCKET).get("Contents", [])]


def _boom(*_: Any, **__: Any) -> None:
    raise ClientError({"Error": {"Code": "InternalError", "Message": "down"}}, "PutObject")


def test_photos_are_durable_in_the_bucket(client: TestClient, setup: Setup, s3: Any) -> None:  # noqa: F811
    order = _create(client, setup)
    url = f"{ORDERS}/{order['id']}/photos"
    uploaded = client.post(
        url, headers=setup.technician, files={"file": ("a.jpg", _jpeg_with_gps(), "image/jpeg")}
    )
    assert uploaded.status_code == 201, uploaded.text
    photo = uploaded.json()

    listing = client.get(url, headers=setup.reception).json()
    assert listing["demo"] is False
    [key] = _keys(s3)
    assert key.endswith(f"/{order['id']}/{photo['id']}.jpg")
    stored = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
    content = client.get(f"{url}/{photo['id']}", headers=setup.reception)
    assert content.status_code == 200
    assert content.content == stored

    assert client.delete(f"{url}/{photo['id']}", headers=setup.technician).status_code == 204
    assert _keys(s3) == []


def test_failed_upload_leaves_no_photo(
    client: TestClient,
    setup: Setup,  # noqa: F811
    storage: S3Storage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order = _create(client, setup)
    url = f"{ORDERS}/{order['id']}/photos"
    monkeypatch.setattr(storage._client, "put_object", _boom)
    failed = client.post(
        url, headers=setup.technician, files={"file": ("a.jpg", _jpeg_with_gps(), "image/jpeg")}
    )
    assert failed.status_code == 503
    assert "No fue posible guardar la foto" in failed.json()["detail"]
    assert client.get(url, headers=setup.reception).json()["items"] == []


def test_failed_delete_keeps_the_photo(
    client: TestClient,
    setup: Setup,  # noqa: F811
    storage: S3Storage,
    s3: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order = _create(client, setup)
    url = f"{ORDERS}/{order['id']}/photos"
    photo = client.post(
        url, headers=setup.technician, files={"file": ("a.jpg", _jpeg_with_gps(), "image/jpeg")}
    ).json()
    monkeypatch.setattr(storage._client, "delete_object", _boom)
    failed = client.delete(f"{url}/{photo['id']}", headers=setup.technician)
    assert failed.status_code == 503
    # The row and the file stay, so the deletion can be retried.
    assert [p["id"] for p in client.get(url, headers=setup.reception).json()["items"]] == [
        photo["id"]
    ]
    assert len(_keys(s3)) == 1
