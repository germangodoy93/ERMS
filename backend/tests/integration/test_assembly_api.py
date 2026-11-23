"""PC assembly: catalog import, configurator, assembly order through delivery."""

from datetime import date
from typing import Any

from fastapi.testclient import TestClient

from .conftest import Shop, new_customer

API = "/api/v1/assembly"
BOM = chr(0xFEFF)
CRLF = chr(13) + chr(10)
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
        {"sku": sku, "name": name, "category": cat, "cost": str(int(p) + price_bump),
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
                             "cost": "1", "specs": {"socket": "AM5"}}]},
        )
    )  # fmt: skip
    assert bad["created"] == 0
    assert bad["errors"][0].startswith("X-1: Especificaciones inválidas para Procesador")

    catalog = _ok(client.get(f"{API}/catalog", headers=shop.tech))
    cpu = next(p for p in catalog if p["sku"] == "ENS-CPU-C20")
    # Supplier cost 2.000.000 + 15 % = 2.300.000 (rounded up to the next $1.000).
    assert cpu["sale_price"] == "2300000.00"
    assert cpu["specs"]["socket"] == "AM5"
    assert "unit_cost" not in cpu  # the configurator never shows the cost
    # Editing the part from the old inventory form keeps its specs; the price follows the cost.
    _ok(
        client.put(
            f"/api/v1/inventory/parts/{cpu['id']}",
            headers=shop.admin,
            json={"sku": cpu["sku"], "name": cpu["name"], "kind": "COMPONENT",
                  "unit_cost": "1999000", "sale_price": "1", "tax_rate": 19,
                  "price_includes_tax": True},
        )
    )  # fmt: skip
    part = _ok(client.get(f"/api/v1/inventory/parts/{cpu['id']}", headers=shop.admin))
    assert (part["assembly_category"], part["specs"]["cores"]) == ("CPU", 8)
    assert (part["unit_cost"], part["sale_price"], part["price_locked"]) == (
        "1999000.00",
        "2299000.00",
        False,
    )
    tech_view = _ok(client.get(f"/api/v1/inventory/parts/{cpu['id']}", headers=shop.tech))
    assert tech_view["unit_cost"] is None
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
    assert result["price"] == "11180000.00"  # sale prices: cost + 15 %
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
    assert draft["total"] == "11330000.00"  # 11.180.000 in parts + 150.000 labor
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
    assert billing["balance"] == "11330000.00"
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


def test_prices_follow_cost_and_margin_unless_fixed(client: TestClient, shop: Shop) -> None:
    _ok(_import(client, shop))
    catalog = {p["sku"]: p for p in _ok(client.get(f"{API}/catalog", headers=shop.tech))}
    gpu = catalog["ENS-GPU-G11"]
    assert gpu["sale_price"] == "3909000.00"  # 3.399.000 + 15 % = 3.908.850 -> 3.909.000
    # Fix the GPU price by hand: it survives new costs and a new margin.
    _ok(
        client.put(
            f"/api/v1/inventory/parts/{gpu['id']}",
            headers=shop.admin,
            json={"sku": gpu["sku"], "name": gpu["name"], "kind": "COMPONENT",
                  "unit_cost": "3399000", "sale_price": "3850000", "tax_rate": 19,
                  "price_includes_tax": True, "price_locked": True},
        )
    )  # fmt: skip
    margin = {"assembly_margin_percent": "20"}
    _ok(client.patch("/api/v1/organization", headers=shop.admin, json=margin))
    catalog = {p["sku"]: p for p in _ok(client.get(f"{API}/catalog", headers=shop.tech))}
    assert catalog["ENS-GPU-G11"]["sale_price"] == "3850000.00"
    assert catalog["ENS-CPU-C20"]["sale_price"] == "2399000.00"  # 1.999.000 + 20 % = 2.398.800
    org = _ok(client.get("/api/v1/organization", headers=shop.admin))
    assert org["assembly_margin_percent"] == "20.00"

    # A new purchase updates the cost and, with it, the price of parts not fixed by hand.
    _ok(
        client.post(
            "/api/v1/inventory/entries",
            headers=shop.admin,
            json={"received_on": date.today().isoformat(),
                  "lines": [{"part_id": catalog["ENS-CPU-C20"]["id"], "quantity": 1,
                             "unit_cost": "1800000"}]},
        ),
        201,
    )  # fmt: skip
    cpu_id = catalog["ENS-CPU-C20"]["id"]
    cpu = _ok(client.get(f"/api/v1/inventory/parts/{cpu_id}", headers=shop.admin))
    assert (cpu["unit_cost"], cpu["sale_price"]) == ("1800000.00", "2160000.00")


def test_cost_template_and_update_from_excel(client: TestClient, shop: Shop) -> None:
    _ok(_import(client, shop))
    assert client.get(f"{API}/catalog/costs.csv", headers=shop.tech).status_code == 403
    template = client.get(f"{API}/catalog/costs.csv", headers=shop.admin)
    assert template.status_code == 200
    text = template.content.decode("utf-8")
    assert text.startswith(BOM + "Código;Nombre;Categoría;Costo;Precio de venta;Precio fijado")
    assert "ENS-CPU-C20;AMD Ryzen 7 9800X3D;Procesador;1999000;2299000;No" in text

    # Excel in Spanish may save Windows-1252 with ";" and the supplier's number format.
    rows = [
        "Código;Nombre;Costo",
        "ENS-CPU-C20;Ryzen;$ 1,899,000",
        "ens-psu-p6;Fuente;407.000",
        "NO-EXISTE;X;100",
        "ENS-RAM-R4;RAM;gratis",
        ";;",
    ]
    upload = (CRLF.join(rows) + CRLF).encode("cp1252")
    result = _ok(
        client.post(
            f"{API}/catalog/costs",
            headers=shop.admin,
            files={"file": ("costos.csv", upload, "text/csv")},
        )
    )
    assert (result["updated"], result["unchanged"]) == (1, 1)
    assert result["unknown"] == ["NO-EXISTE"]
    assert result["errors"] == ["Fila 5 (ENS-RAM-R4): costo inválido."]
    catalog = {p["sku"]: p for p in _ok(client.get(f"{API}/catalog", headers=shop.tech))}
    assert catalog["ENS-CPU-C20"]["sale_price"] == "2184000.00"  # 1.899.000 + 15 % = 2.183.850
    no_columns = client.post(
        f"{API}/catalog/costs",
        headers=shop.admin,
        files={"file": ("x.csv", ("a,b" + CRLF + "1,2" + CRLF).encode(), "text/csv")},
    )
    assert no_columns.status_code == 422
    assert "columnas Código y Costo" in no_columns.json()["detail"]


SETUP = [
    ("ENS-MONITOR-M14", 'XPG 27" Rift 180 Hz QHD', "MONITOR", "749000",
     {"inches": 27, "resolution": "QHD", "hz": 180, "style": {"white": False}}),
    ("ENS-MONITOR-M19", 'ASUS ProArt PA278 27" QHD', "MONITOR", "1189000",
     {"inches": 27, "resolution": "QHD", "pro": True}),
    ("ENS-KEYBOARD-K32", "Razer BlackWidow V4 75%", "KEYBOARD", "799000", {"size": "75%"}),
    ("ENS-DESK-E3", "Cougar E-Grave 160", "DESK", "1099000",
     {"width_cm": 160, "style": {"finish": "black", "rgb": True}}),
]  # fmt: skip


def test_setup_is_priced_apart_and_sold_with_the_pc(client: TestClient, shop: Shop) -> None:
    _ok(_import(client, shop))
    items = [
        {"sku": sku, "name": name, "category": cat, "cost": cost, "specs": specs}
        for sku, name, cat, cost, specs in SETUP
    ]
    _ok(client.post(f"{API}/catalog/import", headers=shop.admin, json={"items": items}))
    catalog = {p["sku"]: p for p in _ok(client.get(f"{API}/catalog", headers=shop.tech))}
    assert catalog["ENS-MONITOR-M14"]["specs"]["style"] == {"white": False}
    selection = _selection(client, shop) | {
        "monitor": [catalog["ENS-MONITOR-M14"]["id"], catalog["ENS-MONITOR-M19"]["id"]],
        "keyboard": catalog["ENS-KEYBOARD-K32"]["id"],
        "desk": catalog["ENS-DESK-E3"]["id"],
        "desk_shape": "L",
        "pc_position": "FLOOR",
    }
    result = _ok(client.post(f"{API}/evaluate", headers=shop.tech, json={"selection": selection}))
    assert result["price"] == "11180000.00"  # the PC alone
    # 862.000 + 1.368.000 + 919.000 + 1.264.000 (cost + 15 %, rounded up)
    assert result["setup_price"] == "4413000.00"
    assert result["ready"] is True
    wrong = selection | {"keyboard": catalog["ENS-DESK-E3"]["id"]}
    assert (
        client.post(f"{API}/evaluate", headers=shop.tech, json={"selection": wrong}).status_code
        == 422
    )
    too_many = selection | {"monitor": [catalog["ENS-MONITOR-M14"]["id"]] * 4}
    assert (
        client.post(f"{API}/evaluate", headers=shop.tech, json={"selection": too_many}).status_code
        == 422
    )

    build = _ok(
        client.post(
            f"{API}/builds",
            headers=shop.tech,
            json={"name": "PC + setup", "selection": selection, "labor_price": "100000"},
        ),
        201,
    )
    assert build["selection"]["desk_shape"] == "L"
    assert build["selection"]["pc_position"] == "FLOOR"
    assert len(build["selection"]["monitor"]) == 2
    assert build["price"] == "15593000.00"  # PC + setup

    customer = _ok(
        client.post(
            "/api/v1/customers",
            headers=shop.reception,
            json=new_customer(id_type=None, id_number=None, full_name="Cliente Setup"),
        ),
        201,
    )
    order = _ok(
        client.post(
            f"{API}/builds/{build['id']}/order",
            headers=shop.tech,
            json={"customer_id": customer["id"]},
        ),
        201,
    )
    quote = _ok(client.get(f"{ORDERS}/{order['id']}/quotes", headers=shop.tech))["quotes"][0]
    assert len(quote["items"]) == 13  # 8 PC parts + 4 setup + labor
    assert quote["total"] == "15693000.00"
    checklist = _ok(client.get(f"{ORDERS}/{order['id']}/assembly", headers=shop.tech))
    assert "monitor" not in [s["code"] for s in checklist["steps"]]  # setup is not assembled
