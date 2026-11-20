from typing import Any

from app.modules.diagnostics import catalog
from app.modules.diagnostics.agent_schemas import AgentReport
from app.modules.diagnostics.catalog import Result
from app.modules.diagnostics.evaluation import evaluate

GB = 1024**3


def _report(**overrides: Any) -> AgentReport:
    data: dict[str, Any] = {
        "agent_version": "0.1.0",
        "elevated": False,
        "system": {"manufacturer": "Fabricante", "model": "Modelo X", "os_caption": "Windows 11"},
        "cpus": [{"name": "CPU Ficticia", "cores": 4, "logical_processors": 8}],
        "memory": {"total_bytes": 16 * GB, "modules": [{"capacity_bytes": 8 * GB}] * 2},
        "gpus": [{"name": "GPU Ficticia"}],
        "disks": [{"friendly_name": "SSD", "size_bytes": 512 * GB, "health_status": "Healthy"}],
        "volumes": [{"drive_letter": "C", "size_bytes": 500 * GB, "free_bytes": 200 * GB}],
        "battery": {
            "present": True,
            "design_capacity_mwh": 50000,
            "full_charge_capacity_mwh": 45000,
        },
        "stability": {"unexpected_shutdowns_30d": 0, "bugchecks_30d": 0},
    }
    data.update(overrides)
    return AgentReport.model_validate(data)


def _results(report: AgentReport) -> dict[str, Result]:
    return {e.code: e.result for e in evaluate(report)}


def test_healthy_computer_without_admin() -> None:
    results = _results(_report())
    assert set(results) == {t.code for t in catalog.AGENT_TESTS}
    assert results["AGENT_DISK_SMART"] is Result.NOT_SUPPORTED  # needs administrator
    assert all(r is Result.OK for code, r in results.items() if code != "AGENT_DISK_SMART")


def test_missing_sections_are_never_ok() -> None:
    report = AgentReport.model_validate(
        {"agent_version": "0.1.0", "elevated": False, "errors": {"battery": "Acceso denegado"}}
    )
    evaluations = {e.code: e for e in evaluate(report)}
    assert all(e.result is Result.NOT_SUPPORTED for e in evaluations.values())
    assert "Acceso denegado" in evaluations["AGENT_BATTERY"].observation


def test_battery_wear_thresholds() -> None:
    def battery(full: int) -> Result:
        bat = {"present": True, "design_capacity_mwh": 50000, "full_charge_capacity_mwh": full}
        return _results(_report(battery=bat))["AGENT_BATTERY"]

    assert battery(45000) is Result.OK  # 10 %
    assert battery(39000) is Result.WARNING  # 22 %
    assert battery(25000) is Result.FAIL  # 50 %
    no_battery = _results(_report(battery={"present": False}))["AGENT_BATTERY"]
    assert no_battery is Result.NOT_SUPPORTED


def test_disk_health_and_space() -> None:
    unhealthy = [{"friendly_name": "HDD", "health_status": "Unhealthy"}]
    assert _results(_report(disks=unhealthy))["AGENT_DISK_HEALTH"] is Result.FAIL
    warning = [{"friendly_name": "HDD", "health_status": "Warning"}]
    assert _results(_report(disks=warning))["AGENT_DISK_HEALTH"] is Result.WARNING
    unknown = [{"friendly_name": "HDD", "health_status": None}]
    assert _results(_report(disks=unknown))["AGENT_DISK_HEALTH"] is Result.NOT_SUPPORTED
    full = [{"drive_letter": "C", "size_bytes": 100 * GB, "free_bytes": 5 * GB}]
    assert _results(_report(volumes=full))["AGENT_DISK_SPACE"] is Result.WARNING


def test_smart_with_administrator() -> None:
    fine = [{"disk": "SSD", "temperature_c": 40, "wear_percent": 5, "read_errors": 0}]
    assert _results(_report(elevated=True, smart=fine))["AGENT_DISK_SMART"] is Result.OK
    worn = [{"disk": "SSD", "wear_percent": 90}]
    assert _results(_report(elevated=True, smart=worn))["AGENT_DISK_SMART"] is Result.WARNING
    errors = [{"disk": "HDD", "read_errors": 3}]
    assert _results(_report(elevated=True, smart=errors))["AGENT_DISK_SMART"] is Result.WARNING
    evaluation = next(e for e in evaluate(_report(elevated=True)) if e.code == "AGENT_DISK_SMART")
    assert "no expone" in evaluation.observation


def test_stability() -> None:
    def stability(shutdowns: int, bugchecks: int) -> Result:
        data = {"unexpected_shutdowns_30d": shutdowns, "bugchecks_30d": bugchecks}
        return _results(_report(stability=data))["AGENT_STABILITY"]

    assert stability(0, 0) is Result.OK
    assert stability(2, 0) is Result.WARNING
    assert stability(0, 1) is Result.WARNING
    assert stability(0, 6) is Result.FAIL


def test_catalog_per_category() -> None:
    phone = {t.code for t in catalog.tests_for("PHONE")}
    laptop = {t.code for t in catalog.tests_for("LAPTOP")}
    console = {t.code for t in catalog.tests_for("CONSOLE")}
    assert {"POWER_ON", "TOUCH", "CELL_SIGNAL"} <= phone
    assert not any(code.startswith("AGENT_") for code in phone | console)
    assert {"KEYBOARD", "TOUCHPAD", "AGENT_BATTERY"} <= laptop
    assert {"CONTROLLERS", "DISC_DRIVE"} <= console
    assert all(
        catalog.manual_tests_for(c)
        for c in ("LAPTOP", "DESKTOP", "PHONE", "TABLET", "CONSOLE", "OTHER")
    )
