from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.roles.catalog import RoleCode

from .conftest import Tenant, login, make_tenant, make_user, new_customer, publish_policy

IMEI = "490154203237518"  # documentation example with a valid check digit
OTHER_IMEI = "356938035643809"


def _setup(client: TestClient, tenant: Tenant) -> tuple[dict[str, str], str]:
    publish_policy(client, login(client, tenant.users[RoleCode.ADMIN].email))
    headers = login(client, tenant.users[RoleCode.RECEPTIONIST].email)
    customer = client.post("/api/v1/customers", headers=headers, json=new_customer())
    assert customer.status_code == 201, customer.text
    return headers, customer.json()["id"]


def _manufacturer_id(client: TestClient, headers: dict[str, str], name: str) -> str:
    manufacturers = client.get("/api/v1/catalog/manufacturers", headers=headers).json()
    return str(next(m["id"] for m in manufacturers if m["name"] == name))


def _model(
    client: TestClient,
    headers: dict[str, str],
    name: str = "Galaxy Ficticio S1",
    manufacturer: str = "Samsung",
    category: str = "PHONE",
) -> str:
    response = client.post(
        "/api/v1/catalog/models",
        headers=headers,
        json={
            "manufacturer_id": _manufacturer_id(client, headers, manufacturer),
            "category_code": category,
            "name": name,
        },
    )
    assert response.status_code == 201, response.text
    model_id: str = response.json()["id"]
    return model_id


def test_catalog_is_preloaded(client: TestClient, tenant: Tenant) -> None:
    headers = login(client, tenant.users[RoleCode.TECHNICIAN].email)
    categories = client.get("/api/v1/catalog/categories", headers=headers).json()
    assert [c["code"] for c in categories] == [
        "LAPTOP",
        "DESKTOP",
        "PHONE",
        "TABLET",
        "CONSOLE",
        "OTHER",
    ]
    names = [m["name"] for m in client.get("/api/v1/catalog/manufacturers", headers=headers).json()]
    assert "Apple" in names
    assert "Xiaomi" in names
    assert names == sorted(names, key=str.lower)


def test_catalog_management_permissions(client: TestClient, tenant: Tenant) -> None:
    receptionist = login(client, tenant.users[RoleCode.RECEPTIONIST].email)
    supervisor = login(client, tenant.users[RoleCode.SUPERVISOR].email)
    url = "/api/v1/catalog/manufacturers"
    assert client.post(url, headers=receptionist, json={"name": "Marca X"}).status_code == 403
    created = client.post(url, headers=supervisor, json={"name": "  Marca   Ficticia "})
    assert created.status_code == 201
    assert created.json()["name"] == "Marca Ficticia"
    duplicate = client.post(url, headers=supervisor, json={"name": "marca ficticia"})
    assert duplicate.status_code == 409

    # Reception creates models while registering devices; only the catalog manager edits them.
    model_id = _model(client, receptionist, manufacturer="Marca Ficticia")
    edit = {"name": "Nombre Nuevo"}
    patch_url = f"/api/v1/catalog/models/{model_id}"
    assert client.patch(patch_url, headers=receptionist, json=edit).status_code == 403
    edited = client.patch(patch_url, headers=supervisor, json=edit)
    assert edited.json()["name"] == "Nombre Nuevo"
    assert edited.json()["manufacturer"]["name"] == "Marca Ficticia"
    assert (
        client.post(
            "/api/v1/catalog/models",
            headers=receptionist,
            json={
                "manufacturer_id": created.json()["id"],
                "category_code": "PHONE",
                "name": "NOMBRE NUEVO",
            },
        ).status_code
        == 409
    )

    deactivated = client.patch(
        f"{url}/{created.json()['id']}", headers=supervisor, json={"is_active": False}
    )
    assert deactivated.json()["is_active"] is False
    active = [m["name"] for m in client.get(url, headers=receptionist).json()]
    assert "Marca Ficticia" not in active


def test_models_filters(client: TestClient, tenant: Tenant) -> None:
    headers = login(client, tenant.users[RoleCode.SUPERVISOR].email)
    _model(client, headers, "Galaxy Ficticio S1", "Samsung", "PHONE")
    _model(client, headers, "Galaxy Tab Ficticia", "Samsung", "TABLET")
    _model(client, headers, "ThinkPad Ficticio", "Lenovo", "LAPTOP")

    def names(**params: str) -> list[str]:
        response = client.get("/api/v1/catalog/models", headers=headers, params=params)
        return [m["name"] for m in response.json()]

    samsung = _manufacturer_id(client, headers, "Samsung")
    assert names(manufacturer_id=samsung) == ["Galaxy Ficticio S1", "Galaxy Tab Ficticia"]
    assert names(category="LAPTOP") == ["ThinkPad Ficticio"]
    assert names(q="tab") == ["Galaxy Tab Ficticia"]
    invalid = client.post(
        "/api/v1/catalog/models",
        headers=headers,
        json={"manufacturer_id": samsung, "category_code": "NAVE", "name": "X"},
    )
    assert invalid.status_code == 422


def test_register_device_with_imei_and_serial(client: TestClient, tenant: Tenant) -> None:
    headers, customer_id = _setup(client, tenant)
    model_id = _model(client, headers)
    response = client.post(
        f"/api/v1/customers/{customer_id}/devices",
        headers=headers,
        json={
            "model_id": model_id,
            "imei": "49 015420 323751 8",
            "serial_number": " r58m 12ab ",
            "storage": "128 GB",
            "color": "Negro",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["imei"], body["serial_number"]) == (IMEI, "R58M12AB")
    assert body["model"]["manufacturer"]["name"] == "Samsung"
    assert body["model"]["category"]["code"] == "PHONE"

    devices = client.get(f"/api/v1/customers/{customer_id}/devices", headers=headers).json()
    assert [d["id"] for d in devices] == [body["id"]]


def test_invalid_or_duplicate_imei_is_rejected(client: TestClient, tenant: Tenant) -> None:
    headers, customer_id = _setup(client, tenant)
    model_id = _model(client, headers)
    url = f"/api/v1/customers/{customer_id}/devices"
    bad = client.post(url, headers=headers, json={"model_id": model_id, "imei": "490154203237519"})
    assert bad.status_code == 422

    first = client.post(url, headers=headers, json={"model_id": model_id, "imei": IMEI})
    assert first.status_code == 201
    other_customer = client.post(
        "/api/v1/customers",
        headers=headers,
        json=new_customer(full_name="Otro Cliente", id_number="9000000009"),
    ).json()["id"]
    duplicate = client.post(
        f"/api/v1/customers/{other_customer}/devices",
        headers=headers,
        json={"model_id": model_id, "imei": IMEI},
    )
    assert duplicate.status_code == 409
    assert "Cliente Ficticio Pérez" in duplicate.json()["detail"]


def test_serial_is_unique_per_model(client: TestClient, tenant: Tenant) -> None:
    headers, customer_id = _setup(client, tenant)
    url = f"/api/v1/customers/{customer_id}/devices"
    phone = _model(client, headers)
    laptop = _model(client, headers, "ThinkPad Ficticio", "Lenovo", "LAPTOP")
    assert (
        client.post(
            url, headers=headers, json={"model_id": phone, "serial_number": "ABC123"}
        ).status_code
        == 201
    )
    assert (
        client.post(
            url, headers=headers, json={"model_id": laptop, "serial_number": "ABC123"}
        ).status_code
        == 201
    )
    assert (
        client.post(
            url, headers=headers, json={"model_id": phone, "serial_number": "abc123"}
        ).status_code
        == 409
    )
    # Devices without identifiers are allowed (e.g. a console with an unreadable label).
    assert client.post(url, headers=headers, json={"model_id": phone}).status_code == 201
    assert client.post(url, headers=headers, json={"model_id": phone}).status_code == 201


def test_device_requires_a_customer_who_can_be_served(client: TestClient, tenant: Tenant) -> None:
    headers, customer_id = _setup(client, tenant)
    model_id = _model(client, headers)
    client.post(
        f"/api/v1/customers/{customer_id}/consents",
        headers=headers,
        json={"purpose": "DATA_PROCESSING", "granted": False, "channel": "PAPER"},
    )
    response = client.post(
        f"/api/v1/customers/{customer_id}/devices", headers=headers, json={"model_id": model_id}
    )
    assert response.status_code == 422
    assert "revocó la autorización" in response.json()["detail"]


def test_update_and_search_devices(client: TestClient, tenant: Tenant) -> None:
    headers, customer_id = _setup(client, tenant)
    model_id = _model(client, headers)
    device = client.post(
        f"/api/v1/customers/{customer_id}/devices",
        headers=headers,
        json={"model_id": model_id, "serial_number": "SER-0001", "notes": "Pantalla rayada"},
    ).json()

    updated = client.patch(
        f"/api/v1/devices/{device['id']}",
        headers=headers,
        json={"imei": IMEI, "color": "Azul", "notes": None},
    )
    assert updated.status_code == 200, updated.text
    assert (updated.json()["imei"], updated.json()["color"], updated.json()["notes"]) == (
        IMEI,
        "Azul",
        None,
    )

    technician = login(client, tenant.users[RoleCode.TECHNICIAN].email)
    for q in ("ser-0001", IMEI[:8], "galaxy"):
        found = client.get("/api/v1/devices", headers=technician, params={"q": q}).json()
        assert [d["id"] for d in found["items"]] == [device["id"]], q
        assert found["items"][0]["customer_name"] == "Cliente Ficticio Pérez"
    assert client.get("/api/v1/devices", headers=technician, params={"q": "ab"}).status_code == 422


def test_anonymizing_customer_clears_device_notes(client: TestClient, tenant: Tenant) -> None:
    headers, customer_id = _setup(client, tenant)
    model_id = _model(client, headers)
    device = client.post(
        f"/api/v1/customers/{customer_id}/devices",
        headers=headers,
        json={"model_id": model_id, "imei": IMEI, "notes": "Cliente llama al 3000000001"},
    ).json()
    admin = login(client, tenant.users[RoleCode.ADMIN].email)
    client.post(
        f"/api/v1/customers/{customer_id}/anonymize", headers=admin, json={"channel": "PAPER"}
    )
    after = client.get(f"/api/v1/devices/{device['id']}", headers=admin).json()
    assert after["notes"] is None
    assert after["imei"] == IMEI  # technical history is kept


def test_devices_are_isolated_between_organizations(
    client: TestClient, tenant: Tenant, db: Session
) -> None:
    headers, customer_id = _setup(client, tenant)
    model_id = _model(client, headers)
    device = client.post(
        f"/api/v1/customers/{customer_id}/devices",
        headers=headers,
        json={"model_id": model_id, "imei": IMEI},
    ).json()

    other = make_tenant(db, slug="otro-taller")
    other_headers = login(client, make_user(db, other, RoleCode.ADMIN).email)
    assert client.get(f"/api/v1/devices/{device['id']}", headers=other_headers).status_code == 404
    assert client.get("/api/v1/catalog/models", headers=other_headers).json() == []
    found = client.get("/api/v1/devices", headers=other_headers, params={"q": IMEI}).json()
    assert found["total"] == 0
    # Another workshop may register the same IMEI for its own customer.
    publish_policy(client, other_headers)
    other_customer = client.post(
        "/api/v1/customers", headers=other_headers, json=new_customer()
    ).json()
    other_model = _model(client, other_headers)
    assert (
        client.post(
            f"/api/v1/customers/{other_customer['id']}/devices",
            headers=other_headers,
            json={"model_id": other_model, "imei": IMEI},
        ).status_code
        == 201
    )
    # A model of another organization cannot be used.
    assert (
        client.post(
            f"/api/v1/customers/{other_customer['id']}/devices",
            headers=other_headers,
            json={"model_id": model_id},
        ).status_code
        == 404
    )
