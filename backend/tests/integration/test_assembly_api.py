"""PC assembly: catalog import, configurator, assembly order through delivery."""

from datetime import date
from typing import Any

from fastapi.testclient import TestClient

from .conftest import Shop, new_customer

API = "/api/v1/assembly"
ORDERS = "/api/v1/work-orders"

# The simulator's "Gamer 1440p" preset (prices include VAT).
GAMER = [
    ("ENS-CPU-C20", "AMD Ryzen 7 9800X3D", "CPU", "1999000",
     {"socket": "AM5", "cores": 8, "tdp_w": 162, "integrated_graphics": True,
      "gaming_index": 98, "work_index": 66}),
    ("ENS-BOARD-B8", "MSI Pro B850-S WiFi6E", "BOARD", "789000",
     {"socket": "AM5", "ram_type": "DDR5", "form_factor": "ATX", "ram_slots": 4,
      "m2_slots": 3, "max_ram_mhz": None}),
    ("ENS-RAM-R4", "16 GB DDR5 6000 MHz (1x16)", "RAM", "839000",
     {"ram_type": "DDR5", "modules": 1, "capacity_gb": 16, "mhz": 6000}),
    ("ENS-GPU-G11", "MSI Shadow 3X RTX 5070 12 GB", "GPU", "3399000",
     {"tdp_w": 250, "length_mm": 297, "gaming_index": 75, "power_connector": "16PIN"}),
    ("ENS-STORAGE-S4", "SSD M.2 XPG S70 Blade 1 TB", "STORAGE", "639000", {"interface": "M.2"}),
    ("ENS-PSU-P6", "XPG Core Reactor II VE 850 W Gold", "PSU", "407000",
     {"watts": 850, "form_factor": "ATX"}),
    ("ENS-CASE-K12", "Lian Li Lancool 216X Black", "CASE", "393000",
     {"size": "ATX", "board_form_factors": ["ATX", "mATX", "ITX"], "max_gpu_mm": 392,
      "max_cooler_mm": 180, "max_radiator_mm": 360, "psu_form_factors": ["ATX"],
      "fan_slots": 7}),
    ("ENS-COOLER-F8", "Noctua NH-U12S chromax.black", "COOLER", "415000",
     {"type": "AIR", "height_mm": 158, "tdp_w": 180, "sockets": None, "dual_tower": False,
      "includes_fans": True}),
    ("ENS-BOARD-B10", "ASRock Z890 Pro-A", "BOARD", "925000",
     {"socket": "LGA1851", "ram_type": "DDR5", "form_factor": "ATX", "ram_slots": 4,
      "m2_slots": 3, "max_ram_mhz": None}),
]  # fmt: skip
SLOT = {"CPU": "cpu", "BOARD": "board", "RAM": "ram", "GPU": "gpu", "PSU": "psu",
        "CASE": "case", "COOLER": "cooler"}  # fmt: skip


def _ok(response: Any, code: int = 200) -> Any:
    assert response.status_code == code, response.text
    return response.json()


def _import(client: TestClient, s: Shop, price_bump: int = 0) -> Any:
    items = [
        {"sku": sku, "name": name, "category": cat, "sale_price": str(int(p) + price_bump),
         "specs": specs}
        for sku, name, cat, p, specs in GAMER
    ]  # fmt: skip
    return client.post(f"{API}/catalog/import", headers=s.admin, json={"items": items})


def _selection(client: TestClient, s: Shop) -> dict[str, Any]:
    catalog = {p["sku"]: p for p in _ok(client.get(f"{API}/catalog", headers=s.tech))}
    selection: dict[str, Any] = {"ram_units": 2, "storage": [], "rgb": []}
    for sku, _, cat, _, _ in GAMER:
        if sku == "ENS-BOARD-B10":
            continue
        if cat == "STORAGE":
            selection["storage"].append(catalog[sku]["id"])
        else:
            selection[SLOT[cat]] = catalog[sku]["id"]
    return selection


def test_catalog_import_is_idempotent_and_validated(client: TestClient, shop: Shop) -> None:
    assert _import_status(client, shop.tech) == 403  # needs inventory:manage too
    assert _import_status(client, shop.reception) == 403
    first = _ok(_import(client, shop))
    assert (first["created"], first["updated"], first["errors"]) == (9, 0, [])
    again = _ok(_import(client, shop, price_bump=1000))
    assert (again["created"], again["updated"]) == (0, 9)
    bad = _ok(
        client.post(
            f"{API}/catalog/import",
            headers=shop.admin,
            json={"items": [{"sku": "x-1", "name": "Mala", "category": "CPU",
                             "sale_price": "1", "specs": {"socket": "AM5"}}]},
        )
    )  # fmt: skip
    assert bad["created"] == 0
    assert bad["errors"][0].startswith("X-1: Especificaciones inválidas para Procesador")

    catalog = _ok(client.get(f"{API}/catalog", headers=shop.tech))
    cpu = next(p for p in catalog if p["sku"] == "ENS-CPU-C20")
    assert cpu["sale_price"] == "2000000.00"
    assert cpu["specs"]["socket"] == "AM5"
    # Editing the part from the old inventory form keeps its specs.
    _ok(
        client.put(
            f"/api/v1/inventory/parts/{cpu['id']}",
            headers=shop.admin,
            json={"sku": cpu["sku"], "name": cpu["name"], "kind": "COMPONENT",
                  "sale_price": "1999000", "tax_rate": 19, "price_includes_tax": True},
        )
    )  # fmt: skip
    part = _ok(client.get(f"/api/v1/inventory/parts/{cpu['id']}", headers=shop.admin))
    assert (part["assembly_category"], part["specs"]["cores"]) == ("CPU", 8)
    wrong = client.put(
        f"/api/v1/inventory/parts/{cpu['id']}",
        headers=shop.admin,
        json={"sku": cpu["sku"], "name": cpu["name"], "assembly_category": "GPU",
              "specs": cpu["specs"]},
    )  # fmt: skip
    assert wrong.status_code == 422


def _import_status(client: TestClient, headers: dict[str, str]) -> int:
    status: int = client.post(
        f"{API}/catalog/import", headers=headers, json={"items": []}
    ).status_code
    return status


def test_evaluate_and_candidates(client: TestClient, shop: Shop) -> None:
    _ok(_import(client, shop))
    selection = _selection(client, shop)
    assert client.post(f"{API}/evaluate", headers=shop.reception, json={}).status_code == 403
    result = _ok(
        client.post(
            f"{API}/evaluate",
            headers=shop.tech,
            json={"selection": selection, "profile": "GAMING", "candidates_for": "BOARD"},
        )
    )
    assert result["ready"] is True
    assert result["errors"] == []
    assert result["watts"] == 484
    assert result["price"] == "9719000.00"
    lga = next(
        p["id"]
        for p in _ok(client.get(f"{API}/catalog", headers=shop.tech))
        if p["sku"] == "ENS-BOARD-B10"
    )
    assert list(result["candidates"]) == [lga]
    assert result["candidates"][lga].startswith("Socket incompatible")
    partial = _ok(
        client.post(
            f"{API}/evaluate", headers=shop.tech, json={"selection": {"cpu": selection["cpu"]}}
        )
    )
    assert partial["missing"] == ["BOARD", "RAM", "STORAGE", "PSU", "CASE", "COOLER"]
    wrong_slot = client.post(
        f"{API}/evaluate", headers=shop.tech, json={"selection": {"cpu": selection["board"]}}
    )
    assert wrong_slot.status_code == 422


def test_assembly_order_from_build_to_warranty(client: TestClient, shop: Shop) -> None:
    _ok(_import(client, shop))
    selection = _selection(client, shop)
    incomplete = _ok(
        client.post(
            f"{API}/builds",
            headers=shop.tech,
            json={"name": "Borrador", "selection": {"cpu": selection["cpu"]}},
        ),
        201,
    )
    build = _ok(
        client.post(
            f"{API}/builds",
            headers=shop.tech,
            json={"name": "Gamer de Ana", "profile": "GAMING", "selection": selection,
                  "labor_price": "150000"},
        ),
        201,
    )  # fmt: skip
    assert build["editable"] is True
    assert build["evaluation"]["ready"] is True
    names = [b["name"] for b in _ok(client.get(f"{API}/builds", headers=shop.tech))]
    assert set(names) == {"Borrador", "Gamer de Ana"}

    customer = _ok(
        client.post(
            "/api/v1/customers",
            headers=shop.reception,
            json=new_customer(id_type=None, id_number=None, full_name="Ana Ficticia"),
        ),
        201,
    )
    refused = client.post(
        f"{API}/builds/{incomplete['id']}/order",
        headers=shop.tech,
        json={"customer_id": customer["id"]},
    )
    assert refused.status_code == 422
    assert "Falta: Placa base" in refused.json()["detail"]

    order = _ok(
        client.post(
            f"{API}/builds/{build['id']}/order",
            headers=shop.tech,
            json={"customer_id": customer["id"]},
        ),
        201,
    )
    oid = order["id"]
    assert (order["kind"], order["status"]) == ("ASSEMBLY", "COTIZACION")
    assert order["device"]["model"] == "PC armada a la medida"
    assert order["diagnostic_fee"] == "0.00"
    again = client.put(
        f"{API}/builds/{build['id']}",
        headers=shop.tech,
        json={"name": "Otro", "selection": selection},
    )
    assert again.status_code == 422
    listed = next(
        b for b in _ok(client.get(f"{API}/builds", headers=shop.tech)) if b["id"] == build["id"]
    )
    assert listed["work_order_number"] == order["number"]
    assert client.delete(f"{API}/builds/{build['id']}", headers=shop.tech).status_code == 422

    quotes = _ok(client.get(f"{ORDERS}/{oid}/quotes", headers=shop.tech))
    draft = quotes["quotes"][0]
    assert draft["status"] == "DRAFT"
    assert len(draft["items"]) == 9  # 8 parts + labor
    ram = next(i for i in draft["items"] if i["description"].startswith("16 GB DDR5"))
    assert ram["quantity"] == "2.00"
    assert draft["total"] == "9869000.00"  # 9.719.000 in parts + 150.000 labor
    _ok(client.post(f"{ORDERS}/{oid}/quotes/{draft['id']}/send", headers=shop.admin))
    _ok(
        client.post(
            f"{ORDERS}/{oid}/quotes/{draft['id']}/response",
            headers=shop.admin,
            json={"accepted": True, "channel": "VERBAL"},
        )
    )
    _ok(client.post(f"{ORDERS}/{oid}/status", headers=shop.tech, json={"status": "EN_REPARACION"}))

    checklist = _ok(client.get(f"{ORDERS}/{oid}/assembly", headers=shop.tech))
    assert checklist["can_work"] is True
    assert checklist["parts_consumed"] is False
    assert [s["code"] for s in checklist["steps"]][:3] == ["cpu", "paste", "cool"]
    early = client.post(f"{ORDERS}/{oid}/assembly/steps/cpu", headers=shop.tech)
    assert "Primero descuente las piezas" in early.json()["detail"]
    no_stock = client.post(f"{ORDERS}/{oid}/assembly/consume", headers=shop.tech)
    assert no_stock.status_code == 422
    assert "Existencia insuficiente" in no_stock.json()["detail"]

    catalog = _ok(client.get(f"{API}/catalog", headers=shop.tech))
    _ok(
        client.post(
            "/api/v1/inventory/entries",
            headers=shop.admin,
            json={
                "received_on": date.today().isoformat(),
                "lines": [
                    {"part_id": p["id"], "quantity": 2, "unit_cost": "100000"} for p in catalog
                ],
            },
        ),
        201,
    )
    consumed = _ok(client.post(f"{ORDERS}/{oid}/assembly/consume", headers=shop.tech))
    assert consumed["parts_consumed"] is True
    ram_stock = next(
        p["stock"]
        for p in _ok(client.get(f"{API}/catalog", headers=shop.tech))
        if p["sku"] == "ENS-RAM-R4"
    )
    assert ram_stock == 0  # two units used
    assert client.post(f"{ORDERS}/{oid}/assembly/consume", headers=shop.tech).status_code == 422

    blocked = client.post(f"{ORDERS}/{oid}/assembly/steps/board", headers=shop.tech)
    assert blocked.status_code == 422
    assert blocked.json()["detail"].startswith("Aún no: primero la CPU")
    assert client.post(f"{ORDERS}/{oid}/assembly/steps/nope", headers=shop.tech).status_code == 404
    for step in checklist["steps"]:
        result = _ok(
            client.post(f"{ORDERS}/{oid}/assembly/steps/{step['code']}", headers=shop.tech)
        )
    assert all(s["done"] for s in result["steps"])

    _ok(
        client.post(f"{ORDERS}/{oid}/status", headers=shop.tech, json={"status": "CONTROL_CALIDAD"})
    )
    repair = _ok(client.get(f"{ORDERS}/{oid}/repair", headers=shop.tech))
    _ok(
        client.post(
            f"{ORDERS}/{oid}/repair/quality-checks",
            headers=shop.tech,
            json={
                "results": [
                    {"test_code": t["test_code"], "result": "OK"} for t in repair["qc_tests"]
                ]
            },
        ),
        201,
    )
    _ok(client.post(f"{ORDERS}/{oid}/status", headers=shop.tech, json={"status": "LISTO_ENTREGA"}))
    billing = _ok(client.get(f"{ORDERS}/{oid}/billing", headers=shop.reception))
    assert billing["balance"] == "9869000.00"
    _ok(
        client.post(
            f"{ORDERS}/{oid}/payments",
            headers=shop.reception,
            json={"amount": billing["balance"], "method": "TRANSFER"},
        ),
        201,
    )
    _ok(
        client.post(
            f"{ORDERS}/{oid}/delivery", headers=shop.reception, json={"picked_up_by_customer": True}
        )
    )
    warranty = _ok(client.get(f"{ORDERS}/{oid}/warranty", headers=shop.reception))
    assert warranty["warranty"]["days"] == 90


def test_assembly_is_for_technicians_and_admins(client: TestClient, shop: Shop) -> None:
    assert client.get(f"{API}/catalog", headers=shop.reception).status_code == 403
    assert client.get(f"{API}/builds", headers=shop.supervisor).status_code == 403
    assert client.get(f"{API}/builds", headers=shop.admin).status_code == 200
    assert client.get(f"{API}/builds", headers=shop.tech).status_code == 200
