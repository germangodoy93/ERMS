import json
from typing import Any

import pytest

from erms_agent import VERSION, collect

BATTERY_XML = """<?xml version="1.0" encoding="utf-8"?>
<BatteryReport xmlns="http://schemas.microsoft.com/battery/2012">
  <Batteries>
    <Battery>
      <Id>Batería ficticia</Id>
      <DesignCapacity>54002</DesignCapacity>
      <FullChargeCapacity>35842</FullChargeCapacity>
      <CycleCount>213</CycleCount>
    </Battery>
  </Batteries>
</BatteryReport>"""

NO_BATTERY_XML = """<?xml version="1.0"?>
<BatteryReport xmlns="http://schemas.microsoft.com/battery/2012"><Batteries/></BatteryReport>"""


def test_single_object_and_arrays_are_accepted() -> None:
    one = json.dumps({"name": "CPU Ficticia", "cores": 4, "logical_processors": 8})
    many = json.dumps([{"name": "A", "cores": "2"}, {"name": "B", "cores": None}])
    assert collect.parse_cpus(one)[0]["cores"] == 4
    assert [c["cores"] for c in collect.parse_cpus(many)] == [2, None]
    assert collect.parse_cpus("") == []


def test_disk_enums_as_names_or_numbers() -> None:
    names = json.dumps({"friendly_name": "SSD", "media_type": "SSD", "bus_type": "NVMe",
                        "health_status": "Healthy", "size_bytes": 512})  # fmt: skip
    numbers = json.dumps({"friendly_name": "HDD", "media_type": 3, "bus_type": 11,
                          "health_status": 2})  # fmt: skip
    assert collect.parse_disks(names)[0]["health_status"] == "Healthy"
    disk = collect.parse_disks(numbers)[0]
    assert (disk["media_type"], disk["bus_type"], disk["health_status"]) == (
        "HDD",
        "SATA",
        "Unhealthy",
    )


def test_long_text_is_truncated() -> None:
    system, memory = collect.parse_system(
        json.dumps({"model": "x" * 500, "total_memory": "17179869184"})
    )
    assert len(system["model"]) == 200
    assert memory == 17179869184


def test_smart_without_counters_is_not_reported() -> None:
    empty = json.dumps([{"disk": "SSD", "temperature_c": None, "wear_percent": None}])
    assert collect.parse_smart(empty) is None
    data = json.dumps(
        {"disk": "SSD", "temperature_c": 41, "wear_percent": 3, "power_on_hours": 900}
    )
    assert collect.parse_smart(data) == [
        {"disk": "SSD", "temperature_c": 41, "wear_percent": 3, "read_errors": None,
         "write_errors": None, "power_on_hours": 900}
    ]  # fmt: skip


def test_battery_report() -> None:
    assert collect.parse_battery_report(BATTERY_XML) == {
        "present": True,
        "design_capacity_mwh": 54002,
        "full_charge_capacity_mwh": 35842,
        "cycle_count": 213,
    }
    assert collect.parse_battery_report(NO_BATTERY_XML) == {"present": False}


def _fake_runner(outputs: dict[str, Any]) -> collect.Runner:
    def run(script: str) -> str:
        for section, query in collect.QUERIES.items():
            if query == script:
                value = outputs[section]
                if isinstance(value, Exception):
                    raise value
                return json.dumps(value)
        raise AssertionError("unexpected query")

    return run


OUTPUTS: dict[str, Any] = {
    "system": {"manufacturer": "Fabricante", "model": "Modelo", "total_memory": 8589934592},
    "cpus": {"name": "CPU", "cores": 4},
    "memory_modules": [{"capacity_bytes": 4294967296}, {"capacity_bytes": 4294967296}],
    "gpus": {"name": "GPU"},
    "disks": {"friendly_name": "SSD", "health_status": "Healthy"},
    "volumes": {"drive_letter": "C", "size_bytes": 100, "free_bytes": 50},
    "smart": {"disk": "SSD", "temperature_c": 40},
    "stability": {"unexpected_shutdowns_30d": 1, "bugchecks_30d": 0},
}


def test_collect_without_admin_skips_smart() -> None:
    report = collect.collect(run=_fake_runner(OUTPUTS), battery=lambda: BATTERY_XML, elevated=False)
    assert report["agent_version"] == VERSION
    assert report["elevated"] is False
    assert "smart" not in report
    assert report["memory"]["total_bytes"] == 8589934592
    assert len(report["memory"]["modules"]) == 2
    assert report["stability"]["unexpected_shutdowns_30d"] == 1
    assert report["errors"] == {}


def test_failures_are_isolated_per_section() -> None:
    outputs = {**OUTPUTS, "disks": RuntimeError("Acceso denegado"), "smart": RuntimeError("x")}

    def broken_battery() -> str:
        raise RuntimeError("powercfg no generó el informe de batería")

    report = collect.collect(run=_fake_runner(outputs), battery=broken_battery, elevated=True)
    assert report["errors"] == {
        "disks": "Acceso denegado",
        "smart": "x",
        "battery": "powercfg no generó el informe de batería",
    }
    assert "disks" not in report
    assert report["cpus"][0]["name"] == "CPU"


def test_queries_are_read_only() -> None:
    """Guard rail: no command that writes, deletes or changes configuration."""
    forbidden = (
        "Remove-", "Set-", "Format-", "Clear-", "Stop-", "Restart-", "Initialize-",
        "New-Item", "Out-File", "Invoke-Expression", "Start-Process", "reg ", "del ",
    )  # fmt: skip
    for query in collect.QUERIES.values():
        for word in forbidden:
            assert word.lower() not in query.lower(), word


@pytest.mark.parametrize("server", ["http://ejemplo.com", "ftp://x"])
def test_api_requires_https(server: str) -> None:
    from erms_agent import api

    with pytest.raises(api.ApiError, match="HTTPS"):
        api.pair(server, "ABCD-1234")
