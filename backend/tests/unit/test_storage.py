from collections.abc import Iterator
from typing import Any

import boto3
import pytest
from moto import mock_aws
from pydantic import ValidationError

from app.core import storage as storage_module
from app.core.config import Settings
from app.core.storage import LocalStorage, S3Storage, StorageError
from app.modules.health.checks import StorageCheck
from app.modules.health.schemas import ComponentStatus

BUCKET = "erms-fotos-test"
DB = "postgresql://u:p@h/db"


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "database_url": DB,
        "s3_bucket": BUCKET,
        "s3_endpoint": "https://s3.amazonaws.com",
        "s3_region": "us-east-1",
        "s3_access_key_id": "test-key",
        "s3_secret_access_key": "test-secret",
    }
    values.update(overrides)
    return Settings(**values)


@pytest.fixture
def s3() -> Iterator[Any]:
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        yield client


def test_s3_round_trip(s3: Any) -> None:
    store = S3Storage(_settings(), client=s3)
    assert store.demo is False
    store.put("org/photo/order/a.jpg", b"jpeg-bytes")
    head = s3.head_object(Bucket=BUCKET, Key="org/photo/order/a.jpg")
    assert head["ContentType"] == "image/jpeg"
    assert store.get("org/photo/order/a.jpg") == b"jpeg-bytes"
    store.delete("org/photo/order/a.jpg")
    with pytest.raises(StorageError, match="not found"):
        store.get("org/photo/order/a.jpg")
    store.delete("org/photo/order/a.jpg")  # deleting twice is harmless


def test_s3_builds_its_own_client_from_settings(s3: Any) -> None:
    store = S3Storage(_settings(s3_addressing_style="path"))
    store.put("k.jpg", b"x")
    assert s3.get_object(Bucket=BUCKET, Key="k.jpg")["Body"].read() == b"x"


@pytest.mark.parametrize("key", ["../etc/passwd", "/abs.jpg", "a/../b.jpg", "", "ñ.jpg"])
def test_s3_rejects_unsafe_keys(s3: Any, key: str) -> None:
    store = S3Storage(_settings(), client=s3)
    with pytest.raises(StorageError, match="Invalid"):
        store.put(key, b"x")


def test_s3_errors_become_storage_errors(s3: Any) -> None:
    store = S3Storage(_settings(s3_bucket="no-existe"), client=s3)
    with pytest.raises(StorageError):
        store.put("a.jpg", b"x")
    with pytest.raises(StorageError):
        store.ping()


def test_s3_requires_configuration() -> None:
    with pytest.raises(StorageError):
        S3Storage(Settings(database_url=DB))


def test_s3_settings_are_all_or_nothing() -> None:
    with pytest.raises(ValidationError, match="S3_BUCKET"):
        Settings(database_url=DB, s3_bucket=BUCKET)
    with pytest.raises(ValidationError, match="empty or missing: S3_ENDPOINT"):
        _settings(s3_endpoint=" ")
    assert not Settings(database_url=DB).uses_s3
    blank = Settings(
        database_url=DB, s3_bucket="", s3_endpoint="", s3_access_key_id="", s3_secret_access_key=""
    )
    assert not blank.uses_s3
    assert _settings().uses_s3


def test_get_storage_picks_s3_when_configured(monkeypatch: pytest.MonkeyPatch, s3: Any) -> None:
    storage_module.get_storage.cache_clear()
    monkeypatch.setattr(storage_module, "get_settings", _settings)
    try:
        assert isinstance(storage_module.get_storage(), S3Storage)
    finally:
        storage_module.get_storage.cache_clear()
    monkeypatch.setattr(storage_module, "get_settings", lambda: Settings(database_url=DB))
    try:
        assert isinstance(storage_module.get_storage(), LocalStorage)
    finally:
        storage_module.get_storage.cache_clear()


def test_storage_health_check(s3: Any, tmp_path: Any) -> None:
    assert StorageCheck(LocalStorage(tmp_path)).run().status is ComponentStatus.NOT_CONFIGURED
    ok = StorageCheck(S3Storage(_settings(), client=s3)).run()
    assert ok.status is ComponentStatus.OK
    assert ok.critical is False
    down = StorageCheck(S3Storage(_settings(s3_bucket="no-existe"), client=s3)).run()
    assert down.status is ComponentStatus.ERROR
    assert down.detail is not None
    assert "HTTP 404" in down.detail
    assert "test-secret" not in down.detail


def test_pasted_values_are_trimmed() -> None:
    settings = _settings(s3_secret_access_key="test-secret\n", s3_endpoint=" https://e.test ")
    assert settings.s3_endpoint == "https://e.test"
    assert settings.s3_secret_access_key is not None
    assert settings.s3_secret_access_key.get_secret_value() == "test-secret"
