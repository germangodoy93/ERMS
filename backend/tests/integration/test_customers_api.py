import json

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog
from app.modules.customers.models import CustomerConsent
from app.modules.roles.catalog import RoleCode

from .conftest import Tenant, login, make_tenant, make_user, new_customer, publish_policy

CUSTOMERS = "/api/v1/customers"


# --- Organization and privacy policy ------------------------------------------------------


def test_policy_requires_complete_workshop_data(client: TestClient, tenant: Tenant) -> None:
    headers = login(client, tenant.users[RoleCode.ADMIN].email)
    draft = client.get("/api/v1/privacy-policy/draft", headers=headers).json()
    assert "NIT" in draft["missing_fields"]
    assert "[NIT]" in draft["content"]

    response = client.post(
        "/api/v1/privacy-policy", headers=headers, json={"content": draft["content"]}
    )
    assert response.status_code == 422
    assert "Complete los datos del taller" in response.json()["detail"]


def test_organization_data_is_normalized(client: TestClient, tenant: Tenant) -> None:
    headers = login(client, tenant.users[RoleCode.ADMIN].email)
    response = client.patch(
        "/api/v1/organization",
        headers=headers,
        json={"tax_id": "890.903.938", "phone": "300 000 0000", "email": "DATOS@Example.com"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["tax_id"], body["phone"], body["email"]) == (
        "890903938-8",
        "+573000000000",
        "datos@example.com",
    )

    bad = client.patch("/api/v1/organization", headers=headers, json={"tax_id": "890903938-1"})
    assert bad.status_code == 422
    assert "dígito de verificación" in json.dumps(bad.json(), ensure_ascii=False)


def test_publishing_creates_versions_and_authorization_texts(
    client: TestClient, tenant: Tenant
) -> None:
    headers = login(client, tenant.users[RoleCode.ADMIN].email)
    assert client.get("/api/v1/privacy-policy", headers=headers).json() == {
        "policy": None,
        "authorizations": {},
    }
    first = publish_policy(client, headers)
    assert first["version"] == 1
    edited = str(first["content"]) + "\nCláusula adicional de prueba."
    second = client.post("/api/v1/privacy-policy", headers=headers, json={"content": edited})
    assert second.json()["version"] == 2

    current = client.get("/api/v1/privacy-policy", headers=headers).json()
    assert current["policy"]["version"] == 2
    assert "(versión 2)" in current["authorizations"]["DATA_PROCESSING"]
    assert "Taller Ficticio de Pruebas SAS" in current["authorizations"]["PHOTOS"]
    versions = client.get("/api/v1/privacy-policy/versions", headers=headers).json()
    assert [v["version"] for v in versions] == [2, 1]
    old = client.get("/api/v1/privacy-policy/versions/1", headers=headers).json()
    assert "Cláusula adicional" not in old["content"]


def test_only_admin_manages_organization_and_policy(client: TestClient, tenant: Tenant) -> None:
    headers = login(client, tenant.users[RoleCode.SUPERVISOR].email)
    assert client.patch("/api/v1/organization", headers=headers, json={}).status_code == 403
    assert client.get("/api/v1/privacy-policy/draft", headers=headers).status_code == 403
    # Everyone can read the workshop data and the policy in force.
    assert client.get("/api/v1/organization", headers=headers).status_code == 200
    assert client.get("/api/v1/privacy-policy", headers=headers).status_code == 200


# --- Customers ----------------------------------------------------------------------------


def test_customer_cannot_be_registered_without_published_policy(
    client: TestClient, tenant: Tenant
) -> None:
    headers = login(client, tenant.users[RoleCode.RECEPTIONIST].email)
    response = client.post(CUSTOMERS, headers=headers, json=new_customer())
    assert response.status_code == 422
    assert "política de tratamiento de datos" in response.json()["detail"]


def test_receptionist_registers_customer_with_consent(
    client: TestClient, tenant: Tenant, db: Session
) -> None:
    publish_policy(client, login(client, tenant.users[RoleCode.ADMIN].email))
    headers = login(client, tenant.users[RoleCode.RECEPTIONIST].email)
    payload = new_customer(
        email="Cliente@Example.com",
        consents=[
            {"purpose": "DATA_PROCESSING", "channel": "SCREEN"},
            {"purpose": "PHOTOS", "channel": "SCREEN"},
        ],
    )
    response = client.post(CUSTOMERS, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["full_name"] == "Cliente Ficticio Pérez"
    assert (body["id_number"], body["phone"], body["email"]) == (
        "1000000001",
        "+573000000001",
        "cliente@example.com",
    )
    assert body["can_be_served"] is True
    consents = {c["purpose"]: c for c in body["consents"]}
    assert set(consents) == {"DATA_PROCESSING", "PHOTOS"}
    assert consents["DATA_PROCESSING"]["policy_version"] == 1

    # The audit trail records which fields were set, never the personal values.
    log = db.scalar(select(AuditLog).where(AuditLog.action == "customer.created"))
    assert log is not None
    assert log.changes is not None
    dumped = json.dumps(log.changes, ensure_ascii=False)
    for personal in ("Ficticio", "1000000001", "3000000001", "example.com"):
        assert personal not in dumped
    assert "full_name" in log.changes["fields"]


def test_customer_validation_rules(client: TestClient, tenant: Tenant) -> None:
    publish_policy(client, login(client, tenant.users[RoleCode.ADMIN].email))
    headers = login(client, tenant.users[RoleCode.RECEPTIONIST].email)
    cases = {
        "sin autorización": new_customer(consents=[{"purpose": "PHOTOS", "channel": "SCREEN"}]),
        "sin contacto": new_customer(phone=None),
        "documento incompleto": new_customer(id_type="CC", id_number=None),
        "teléfono inválido": new_customer(phone="12345"),
        "NIT inválido": new_customer(kind="COMPANY", id_type="NIT", id_number="890903938-1"),
    }
    for case, payload in cases.items():
        response = client.post(CUSTOMERS, headers=headers, json=payload)
        assert response.status_code == 422, case


def test_document_is_optional_but_unique(client: TestClient, tenant: Tenant) -> None:
    publish_policy(client, login(client, tenant.users[RoleCode.ADMIN].email))
    headers = login(client, tenant.users[RoleCode.RECEPTIONIST].email)
    walk_in = new_customer(id_type=None, id_number=None)
    assert client.post(CUSTOMERS, headers=headers, json=walk_in).status_code == 201
    assert client.post(CUSTOMERS, headers=headers, json=walk_in).status_code == 201

    assert client.post(CUSTOMERS, headers=headers, json=new_customer()).status_code == 201
    duplicate = client.post(
        CUSTOMERS, headers=headers, json=new_customer(id_number="1000000001", full_name="Otro")
    )
    assert duplicate.status_code == 409
    assert "Cliente Ficticio Pérez" in duplicate.json()["detail"]


def test_search_by_name_without_accents_document_and_phone(
    client: TestClient, tenant: Tenant
) -> None:
    publish_policy(client, login(client, tenant.users[RoleCode.ADMIN].email))
    headers = login(client, tenant.users[RoleCode.RECEPTIONIST].email)
    client.post(CUSTOMERS, headers=headers, json=new_customer(full_name="José Muñoz Ficticio"))
    client.post(
        CUSTOMERS,
        headers=headers,
        json=new_customer(full_name="Ana Ejemplo", id_number="2000000002", phone="310 000 0002"),
    )
    client.post(
        CUSTOMERS,
        headers=headers,
        json=new_customer(
            full_name="100% Comodín_Ficticio", id_number="3000000003", phone="310 000 0003"
        ),
    )

    def names(q: str) -> list[str]:
        response = client.get(CUSTOMERS, headers=headers, params={"q": q})
        assert response.status_code == 200
        return [c["full_name"] for c in response.json()["items"]]

    assert names("jose munoz") == ["José Muñoz Ficticio"]
    assert names("MUÑOZ") == ["José Muñoz Ficticio"]
    assert names("2.000.000") == ["Ana Ejemplo"]
    assert names("3100000002") == ["Ana Ejemplo"]
    assert names("100%") == ["100% Comodín_Ficticio"]
    assert names("%") == ["100% Comodín_Ficticio"]

    page = client.get(CUSTOMERS, headers=headers, params={"size": 2, "page": 2}).json()
    assert (page["total"], len(page["items"])) == (3, 1)


def test_update_customer(client: TestClient, tenant: Tenant) -> None:
    publish_policy(client, login(client, tenant.users[RoleCode.ADMIN].email))
    headers = login(client, tenant.users[RoleCode.RECEPTIONIST].email)
    customer_id = client.post(CUSTOMERS, headers=headers, json=new_customer()).json()["id"]

    response = client.patch(
        f"{CUSTOMERS}/{customer_id}",
        headers=headers,
        json={"full_name": "Nombre Corregido", "address": "Carrera Ficticia 4", "is_active": False},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["full_name"], body["is_active"], body["can_be_served"]) == (
        "Nombre Corregido",
        False,
        False,
    )
    removing_contact = client.patch(
        f"{CUSTOMERS}/{customer_id}", headers=headers, json={"phone": None}
    )
    assert removing_contact.status_code == 422


def test_revoke_and_grant_consent_again(client: TestClient, tenant: Tenant, db: Session) -> None:
    publish_policy(client, login(client, tenant.users[RoleCode.ADMIN].email))
    headers = login(client, tenant.users[RoleCode.RECEPTIONIST].email)
    customer_id = client.post(CUSTOMERS, headers=headers, json=new_customer()).json()["id"]
    url = f"{CUSTOMERS}/{customer_id}/consents"

    revoked = client.post(
        url,
        headers=headers,
        json={"purpose": "DATA_PROCESSING", "granted": False, "channel": "PAPER"},
    )
    assert revoked.status_code == 200
    assert revoked.json()["can_be_served"] is False
    again = client.post(
        url,
        headers=headers,
        json={"purpose": "DATA_PROCESSING", "granted": False, "channel": "PAPER"},
    )
    assert again.status_code == 409
    never_granted = client.post(
        url, headers=headers, json={"purpose": "PHOTOS", "granted": False, "channel": "PAPER"}
    )
    assert never_granted.status_code == 422

    granted = client.post(
        url,
        headers=headers,
        json={"purpose": "DATA_PROCESSING", "granted": True, "channel": "VERBAL"},
    )
    assert granted.json()["can_be_served"] is True

    history = client.get(url, headers=headers).json()
    assert [(h["granted"], h["channel"]) for h in history] == [
        (True, "VERBAL"),
        (False, "PAPER"),
        (True, "SCREEN"),
    ]
    assert history[0]["recorded_by"] == tenant.users[RoleCode.RECEPTIONIST].full_name
    # Append-only: three rows, none updated.
    rows = db.scalars(select(CustomerConsent).where(CustomerConsent.customer_id == customer_id))
    assert len(list(rows)) == 3


def test_anonymize_removes_personal_data(client: TestClient, tenant: Tenant, db: Session) -> None:
    admin = login(client, tenant.users[RoleCode.ADMIN].email)
    publish_policy(client, admin)
    customer = client.post(
        CUSTOMERS,
        headers=admin,
        json=new_customer(
            email="cliente@example.com",
            address="Dirección Ficticia",
            notes="Nota con datos",
            consents=[
                {"purpose": "DATA_PROCESSING", "channel": "SCREEN"},
                {"purpose": "PHOTOS", "channel": "SCREEN"},
            ],
        ),
    ).json()
    url = f"{CUSTOMERS}/{customer['id']}/anonymize"

    supervisor = login(client, tenant.users[RoleCode.SUPERVISOR].email)
    assert client.post(url, headers=supervisor, json={"channel": "PAPER"}).status_code == 403

    response = client.post(url, headers=admin, json={"channel": "PAPER"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["full_name"] == "Cliente anonimizado"
    for field in ("id_type", "id_number", "phone", "email", "address", "notes"):
        assert body[field] is None, field
    assert body["is_active"] is False
    assert body["anonymized_at"] is not None
    assert all(not c["granted"] for c in body["consents"])

    assert client.post(url, headers=admin, json={"channel": "PAPER"}).status_code == 409
    edit = client.patch(f"{CUSTOMERS}/{customer['id']}", headers=admin, json={"full_name": "X Y"})
    assert edit.status_code == 422

    # No personal value survives anywhere in the audit trail of this customer.
    logs = db.scalars(select(AuditLog).where(AuditLog.entity_id == customer["id"])).all()
    assert {log.action for log in logs} == {"customer.created", "customer.anonymized"}
    dumped = json.dumps([log.changes for log in logs], ensure_ascii=False)
    for personal in ("Ficticio", "1000000001", "example.com", "Dirección Ficticia"):
        assert personal not in dumped


def test_permissions_by_role(client: TestClient, tenant: Tenant) -> None:
    publish_policy(client, login(client, tenant.users[RoleCode.ADMIN].email))
    technician = login(client, tenant.users[RoleCode.TECHNICIAN].email)
    assert client.get(CUSTOMERS, headers=technician).status_code == 200
    assert client.post(CUSTOMERS, headers=technician, json=new_customer()).status_code == 403
    supervisor = login(client, tenant.users[RoleCode.SUPERVISOR].email)
    assert client.post(CUSTOMERS, headers=supervisor, json=new_customer()).status_code == 201


def test_customers_are_isolated_between_organizations(
    client: TestClient, tenant: Tenant, db: Session
) -> None:
    publish_policy(client, login(client, tenant.users[RoleCode.ADMIN].email))
    headers = login(client, tenant.users[RoleCode.RECEPTIONIST].email)
    customer_id = client.post(CUSTOMERS, headers=headers, json=new_customer()).json()["id"]

    other = make_tenant(db, slug="otro-taller")
    other_admin = make_user(db, other, RoleCode.ADMIN)
    other_headers = login(client, other_admin.email)
    publish_policy(client, other_headers)
    assert client.get(f"{CUSTOMERS}/{customer_id}", headers=other_headers).status_code == 404
    assert client.get(CUSTOMERS, headers=other_headers).json()["total"] == 0
    # The same document can exist in another organization.
    assert client.post(CUSTOMERS, headers=other_headers, json=new_customer()).status_code == 201
