"""Read-only collection of hardware information on Windows.

Safety rules (docs/ERMS-HLD.md):
- Only queries: CIM/WMI classes through PowerShell, `powercfg /batteryreport` and counts of
  two System event IDs. Nothing is written except a temporary battery report that is deleted.
- No user files, browsing data, installed software, accounts or network identifiers.
- There is no code path that formats, deletes, changes settings or updates firmware.

Each section is collected independently: a failure is recorded in `errors` and the rest
continues. Parsing is separated from execution so it can be unit tested on any OS.
"""

import ctypes
import json
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from typing import Any

from erms_agent import VERSION

Runner = Callable[[str], str]
TIMEOUT_SECONDS = 90

# MSFT_PhysicalDisk enum values (Windows Storage Management API). Windows usually returns the
# names already ("SSD", "Healthy"); the numeric form is mapped for older builds.
HEALTH = {0: "Healthy", 1: "Warning", 2: "Unhealthy", 5: "Unknown"}
MEDIA = {0: "Unspecified", 3: "HDD", 4: "SSD", 5: "SCM"}
BUS = {
    1: "SCSI", 2: "ATAPI", 3: "ATA", 4: "1394", 5: "SSA", 6: "Fibre Channel", 7: "USB",
    8: "RAID", 9: "iSCSI", 10: "SAS", 11: "SATA", 12: "SD", 13: "MMC", 15: "File Backed",
    16: "Storage Spaces", 17: "NVMe", 18: "SCM", 19: "UFS",
}  # fmt: skip

QUERIES: dict[str, str] = {
    "system": (
        "$os=Get-CimInstance Win32_OperatingSystem; $cs=Get-CimInstance Win32_ComputerSystem; "
        "$b=Get-CimInstance Win32_BIOS; [pscustomobject]@{"
        "os_caption=$os.Caption; os_version=$os.Version; os_build=$os.BuildNumber; "
        "architecture=$os.OSArchitecture; manufacturer=$cs.Manufacturer; model=$cs.Model; "
        "bios_serial=$b.SerialNumber; bios_version=$b.SMBIOSBIOSVersion; "
        "last_boot=$os.LastBootUpTime.ToString('o'); total_memory=$cs.TotalPhysicalMemory}"
    ),
    "cpus": (
        "@(Get-CimInstance Win32_Processor | ForEach-Object {[pscustomobject]@{"
        "name=$_.Name; cores=$_.NumberOfCores; logical_processors=$_.NumberOfLogicalProcessors; "
        "max_clock_mhz=$_.MaxClockSpeed}})"
    ),
    "memory_modules": (
        "@(Get-CimInstance Win32_PhysicalMemory | ForEach-Object {[pscustomobject]@{"
        "capacity_bytes=$_.Capacity; speed_mhz=$_.Speed; manufacturer=$_.Manufacturer; "
        "part_number=$_.PartNumber}})"
    ),
    "gpus": (
        "@(Get-CimInstance Win32_VideoController | ForEach-Object {[pscustomobject]@{"
        "name=$_.Name; driver_version=$_.DriverVersion; adapter_ram_bytes=$_.AdapterRAM}})"
    ),
    "disks": (
        "@(Get-PhysicalDisk | ForEach-Object {[pscustomobject]@{"
        "friendly_name=$_.FriendlyName; media_type=[string]$_.MediaType; "
        "bus_type=[string]$_.BusType; size_bytes=$_.Size; health_status=[string]$_.HealthStatus; "
        "operational_status=[string]($_.OperationalStatus -join ',')}})"
    ),
    "volumes": (
        "@(Get-Volume | Where-Object {$_.DriveLetter} | ForEach-Object {[pscustomobject]@{"
        "drive_letter=[string]$_.DriveLetter; size_bytes=$_.Size; free_bytes=$_.SizeRemaining; "
        "file_system=$_.FileSystem}})"
    ),
    # Requires administrator: Windows denies reliability counters to standard users.
    "smart": (
        "@(Get-PhysicalDisk | ForEach-Object {$r = $_ | Get-StorageReliabilityCounter; "
        "[pscustomobject]@{disk=$_.FriendlyName; temperature_c=$r.Temperature; "
        "wear_percent=$r.Wear; read_errors=$r.ReadErrorsTotal; write_errors=$r.WriteErrorsTotal; "
        "power_on_hours=$r.PowerOnHours}})"
    ),
    # Only counts; the content of the events is never read.
    "stability": (
        "$since=(Get-Date).AddDays(-30); "
        "$k=@(Get-WinEvent -FilterHashtable @{LogName='System'; "
        "ProviderName='Microsoft-Windows-Kernel-Power'; Id=41; StartTime=$since} "
        "-ErrorAction SilentlyContinue).Count; "
        "$b=@(Get-WinEvent -FilterHashtable @{LogName='System'; "
        "ProviderName='Microsoft-Windows-WER-SystemErrorReporting'; Id=1001; StartTime=$since} "
        "-ErrorAction SilentlyContinue).Count; "
        "[pscustomobject]@{unexpected_shutdowns_30d=$k; bugchecks_30d=$b}"
    ),
}


def powershell(script: str) -> str:
    """Runs a fixed query and returns its JSON output."""
    command = (
        "[Console]::OutputEncoding=[Text.Encoding]::UTF8; $ErrorActionPreference='Stop'; "
        f"$({script}) | ConvertTo-Json -Depth 4 -Compress"
    )
    completed = subprocess.run(  # noqa: S603 - fixed executable and arguments
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],  # noqa: S607
        capture_output=True,
        timeout=TIMEOUT_SECONDS,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout).strip().splitlines()
        raise RuntimeError(message[0] if message else f"código {completed.returncode}")
    return completed.stdout


def is_elevated() -> bool:
    windll = getattr(ctypes, "windll", None)  # only exists on Windows
    if windll is None:
        return False
    try:
        return bool(windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


# --- Parsing (pure) ------------------------------------------------------------------------


def _json(text: str) -> Any:
    text = text.strip()
    return json.loads(text) if text else None


def _list(value: Any) -> list[dict[str, Any]]:
    """ConvertTo-Json emits an object for one item and an array for several."""
    if value is None:
        return []
    return [v for v in (value if isinstance(value, list) else [value]) if isinstance(v, dict)]


def _int(value: Any) -> int | None:
    try:
        return int(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def _str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:200] or None


def _enum(value: Any, names: dict[int, str]) -> str | None:
    number = _int(value)
    if number is None:
        return _str(value)
    return names.get(number, str(number))


def parse_system(text: str) -> tuple[dict[str, Any], int | None]:
    data = _json(text) or {}
    system = {
        key: _str(data.get(key))
        for key in (
            "os_caption", "os_version", "os_build", "architecture", "manufacturer", "model",
            "bios_serial", "bios_version", "last_boot",
        )
    }  # fmt: skip
    return system, _int(data.get("total_memory"))


def parse_cpus(text: str) -> list[dict[str, Any]]:
    return [
        {
            "name": _str(c.get("name")),
            "cores": _int(c.get("cores")),
            "logical_processors": _int(c.get("logical_processors")),
            "max_clock_mhz": _int(c.get("max_clock_mhz")),
        }
        for c in _list(_json(text))
    ]


def parse_memory_modules(text: str) -> list[dict[str, Any]]:
    return [
        {
            "capacity_bytes": _int(m.get("capacity_bytes")),
            "speed_mhz": _int(m.get("speed_mhz")),
            "manufacturer": _str(m.get("manufacturer")),
            "part_number": _str(m.get("part_number")),
        }
        for m in _list(_json(text))
    ]


def parse_gpus(text: str) -> list[dict[str, Any]]:
    return [
        {
            "name": _str(g.get("name")),
            "driver_version": _str(g.get("driver_version")),
            "adapter_ram_bytes": _int(g.get("adapter_ram_bytes")),
        }
        for g in _list(_json(text))
    ]


def parse_disks(text: str) -> list[dict[str, Any]]:
    return [
        {
            "friendly_name": _str(d.get("friendly_name")),
            "media_type": _enum(d.get("media_type"), MEDIA),
            "bus_type": _enum(d.get("bus_type"), BUS),
            "size_bytes": _int(d.get("size_bytes")),
            "health_status": _enum(d.get("health_status"), HEALTH),
            "operational_status": _str(d.get("operational_status")),
        }
        for d in _list(_json(text))
    ]


def parse_volumes(text: str) -> list[dict[str, Any]]:
    return [
        {
            "drive_letter": (_str(v.get("drive_letter")) or "")[:4] or None,
            "size_bytes": _int(v.get("size_bytes")),
            "free_bytes": _int(v.get("free_bytes")),
            "file_system": (_str(v.get("file_system")) or "")[:20] or None,
        }
        for v in _list(_json(text))
    ]


def parse_smart(text: str) -> list[dict[str, Any]] | None:
    rows = [
        {
            "disk": _str(s.get("disk")),
            "temperature_c": _int(s.get("temperature_c")),
            "wear_percent": _int(s.get("wear_percent")),
            "read_errors": _int(s.get("read_errors")),
            "write_errors": _int(s.get("write_errors")),
            "power_on_hours": _int(s.get("power_on_hours")),
        }
        for s in _list(_json(text))
    ]
    # A disk that exposes no counter at all is not "healthy": report nothing for it.
    useful = [r for r in rows if any(r[k] is not None for k in r if k != "disk")]
    return useful or None


def parse_stability(text: str) -> dict[str, int]:
    data = _json(text) or {}
    return {
        "unexpected_shutdowns_30d": _int(data.get("unexpected_shutdowns_30d")) or 0,
        "bugchecks_30d": _int(data.get("bugchecks_30d")) or 0,
    }


def parse_battery_report(xml_text: str) -> dict[str, Any]:
    """Parses `powercfg /batteryreport /xml`. Only capacities and cycles are read."""
    root = ET.fromstring(xml_text)  # noqa: S314 - local file generated by Windows itself
    batteries = [el for el in root.iter() if el.tag.rsplit("}", 1)[-1] == "Battery"]
    if not batteries:
        return {"present": False}

    def field(battery: ET.Element, name: str) -> int | None:
        for el in battery:
            if el.tag.rsplit("}", 1)[-1] == name:
                return _int(el.text)
        return None

    first = batteries[0]
    return {
        "present": True,
        "design_capacity_mwh": field(first, "DesignCapacity"),
        "full_charge_capacity_mwh": field(first, "FullChargeCapacity"),
        "cycle_count": field(first, "CycleCount"),
    }


def battery_report() -> str:
    with tempfile.TemporaryDirectory(prefix="erms-") as folder:
        output = Path(folder) / "battery.xml"
        completed = subprocess.run(  # noqa: S603 - fixed executable and arguments
            ["powercfg", "/batteryreport", "/xml", "/output", str(output)],  # noqa: S607
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
        if completed.returncode != 0 or not output.exists():
            raise RuntimeError("powercfg no generó el informe de batería")
        return output.read_text(encoding="utf-8", errors="replace")


# --- Orchestration -------------------------------------------------------------------------


def collect(
    run: Runner = powershell,
    battery: Callable[[], str] = battery_report,
    elevated: bool | None = None,
    progress: Callable[[str], None] = lambda _: None,
) -> dict[str, Any]:
    admin = is_elevated() if elevated is None else elevated
    report: dict[str, Any] = {"agent_version": VERSION, "elevated": admin, "errors": {}}
    errors: dict[str, str] = report["errors"]

    def attempt(section: str, label: str, action: Callable[[], Any]) -> Any:
        progress(label)
        try:
            return action()
        except Exception as exc:
            errors[section] = str(exc)[:200] or exc.__class__.__name__
            return None

    system = attempt("system", "Sistema y equipo", lambda: parse_system(run(QUERIES["system"])))
    total_memory = None
    if system:
        report["system"], total_memory = system
    report["cpus"] = attempt("cpus", "Procesador", lambda: parse_cpus(run(QUERIES["cpus"])))
    modules = attempt(
        "memory", "Memoria", lambda: parse_memory_modules(run(QUERIES["memory_modules"]))
    )
    if total_memory or modules:
        report["memory"] = {"total_bytes": total_memory, "modules": modules or []}
    report["gpus"] = attempt("gpus", "Tarjeta de video", lambda: parse_gpus(run(QUERIES["gpus"])))
    report["disks"] = attempt("disks", "Discos", lambda: parse_disks(run(QUERIES["disks"])))
    report["volumes"] = attempt(
        "volumes", "Espacio en disco", lambda: parse_volumes(run(QUERIES["volumes"]))
    )
    if admin:
        report["smart"] = attempt(
            "smart", "SMART de discos", lambda: parse_smart(run(QUERIES["smart"]))
        )
    report["battery"] = attempt("battery", "Batería", lambda: parse_battery_report(battery()))
    report["stability"] = attempt(
        "stability", "Estabilidad (30 días)", lambda: parse_stability(run(QUERIES["stability"]))
    )
    return {k: v for k, v in report.items() if v is not None}


def running_on_windows() -> bool:
    return os.name == "nt"
