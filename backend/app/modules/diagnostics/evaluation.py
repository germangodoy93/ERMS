"""Turns what the agent collected into diagnostic results. Pure functions, unit tested.

The rule is: evaluate only what was read. A missing section is NOT_SUPPORTED with the reason,
never OK by default.
"""

from dataclasses import dataclass, field
from typing import Any

from app.modules.diagnostics import catalog as c
from app.modules.diagnostics.agent_schemas import AgentReport
from app.modules.diagnostics.catalog import Result

GB = 1024**3


@dataclass(frozen=True, slots=True)
class Evaluation:
    code: str
    result: Result
    observation: str
    evidence: dict[str, Any] = field(default_factory=dict)


def _gb(value: int | None) -> str:
    return f"{value / GB:.1f} GB" if value else "?"


def _unsupported(code: str, reason: str, report: AgentReport, section: str) -> Evaluation:
    error = report.errors.get(section)
    return Evaluation(code, Result.NOT_SUPPORTED, f"{reason}{f' ({error})' if error else ''}")


def evaluate(report: AgentReport) -> list[Evaluation]:
    return [
        _system(report),
        _cpu(report),
        _memory(report),
        _gpu(report),
        _disk_health(report),
        _disk_space(report),
        _smart(report),
        _battery(report),
        _stability(report),
    ]


def _system(report: AgentReport) -> Evaluation:
    s = report.system
    if s is None:
        return _unsupported("AGENT_SYSTEM", "No se pudo leer el sistema", report, "system")
    text = " · ".join(
        v
        for v in (
            f"{s.manufacturer or ''} {s.model or ''}".strip() or None,
            s.os_caption,
            f"versión {s.os_version}" if s.os_version else None,
            f"serial BIOS {s.bios_serial}" if s.bios_serial else None,
        )
        if v
    )
    return Evaluation("AGENT_SYSTEM", Result.OK, text, s.model_dump(exclude_none=True))


def _cpu(report: AgentReport) -> Evaluation:
    if not report.cpus:
        return _unsupported("AGENT_CPU", "No se pudo leer el procesador", report, "cpus")
    cpu = report.cpus[0]
    text = (
        f"{cpu.name or 'Procesador'}: {cpu.cores or '?'} núcleos, "
        f"{cpu.logical_processors or '?'} hilos"
    )
    return Evaluation(
        "AGENT_CPU",
        Result.OK,
        text,
        {"cpus": [x.model_dump(exclude_none=True) for x in report.cpus]},
    )


def _memory(report: AgentReport) -> Evaluation:
    m = report.memory
    if m is None or not m.total_bytes:
        return _unsupported("AGENT_MEMORY", "No se pudo leer la memoria", report, "memory")
    modules = len(m.modules)
    text = f"{_gb(m.total_bytes)} en {modules} módulo(s)" if modules else _gb(m.total_bytes)
    return Evaluation("AGENT_MEMORY", Result.OK, text, m.model_dump(exclude_none=True))


def _gpu(report: AgentReport) -> Evaluation:
    if not report.gpus:
        return _unsupported("AGENT_GPU", "No se pudo leer la tarjeta de video", report, "gpus")
    names = ", ".join(g.name or "?" for g in report.gpus)
    return Evaluation(
        "AGENT_GPU",
        Result.OK,
        names,
        {"gpus": [g.model_dump(exclude_none=True) for g in report.gpus]},
    )


def _disk_health(report: AgentReport) -> Evaluation:
    if not report.disks:
        return _unsupported("AGENT_DISK_HEALTH", "No se pudieron leer los discos", report, "disks")
    statuses = [(d.health_status or "").lower() for d in report.disks]
    evidence = {"disks": [d.model_dump(exclude_none=True) for d in report.disks]}
    summary = "; ".join(
        f"{d.friendly_name or 'Disco'} ({_gb(d.size_bytes)}): {d.health_status or 'sin dato'}"
        for d in report.disks
    )
    if any(s == "unhealthy" for s in statuses):
        return Evaluation("AGENT_DISK_HEALTH", Result.FAIL, summary, evidence)
    if any(s == "warning" for s in statuses):
        return Evaluation("AGENT_DISK_HEALTH", Result.WARNING, summary, evidence)
    if all(s == "healthy" for s in statuses):
        return Evaluation("AGENT_DISK_HEALTH", Result.OK, summary, evidence)
    return Evaluation(
        "AGENT_DISK_HEALTH",
        Result.NOT_SUPPORTED,
        f"Windows no reporta el estado de salud: {summary}",
        evidence,
    )


def _disk_space(report: AgentReport) -> Evaluation:
    volumes = [v for v in report.volumes or [] if v.size_bytes and v.free_bytes is not None]
    if not volumes:
        return _unsupported("AGENT_DISK_SPACE", "No se pudo leer el espacio", report, "volumes")
    free = {
        v.drive_letter or "?": round(100 * (v.free_bytes or 0) / (v.size_bytes or 1), 1)
        for v in volumes
    }
    text = ", ".join(f"{letter}: {pct} % libre" for letter, pct in free.items())
    result = Result.WARNING if min(free.values()) < c.DISK_FREE_WARNING else Result.OK
    return Evaluation(
        "AGENT_DISK_SPACE",
        result,
        text,
        {"volumes": [v.model_dump(exclude_none=True) for v in volumes]},
    )


def _smart(report: AgentReport) -> Evaluation:
    if not report.smart:
        reason = (
            "El disco no expone datos SMART a Windows"
            if report.elevated
            else "Requiere ejecutar el agente como administrador"
        )
        return _unsupported("AGENT_DISK_SMART", reason, report, "smart")
    findings: list[str] = []
    for s in report.smart:
        name = s.disk or "Disco"
        if (s.read_errors or 0) > 0 or (s.write_errors or 0) > 0:
            findings.append(f"{name}: errores de lectura/escritura")
        if s.wear_percent is not None and s.wear_percent >= c.SMART_WEAR_WARNING:
            findings.append(f"{name}: desgaste {s.wear_percent} %")
        if s.temperature_c is not None and s.temperature_c >= c.SMART_TEMP_WARNING:
            findings.append(f"{name}: temperatura {s.temperature_c} °C")
    details = "; ".join(
        f"{s.disk or 'Disco'}: "
        + ", ".join(
            part
            for part in (
                f"{s.temperature_c} °C" if s.temperature_c is not None else None,
                f"desgaste {s.wear_percent} %" if s.wear_percent is not None else None,
                f"{s.power_on_hours} h de uso" if s.power_on_hours is not None else None,
            )
            if part
        )
        for s in report.smart
    )
    evidence = {"smart": [s.model_dump(exclude_none=True) for s in report.smart]}
    if findings:
        return Evaluation("AGENT_DISK_SMART", Result.WARNING, "; ".join(findings), evidence)
    return Evaluation("AGENT_DISK_SMART", Result.OK, details or "Sin alertas", evidence)


def _battery(report: AgentReport) -> Evaluation:
    b = report.battery
    if b is None:
        return _unsupported("AGENT_BATTERY", "No se pudo leer la batería", report, "battery")
    if not b.present:
        return Evaluation("AGENT_BATTERY", Result.NOT_SUPPORTED, "El equipo no tiene batería")
    if not b.design_capacity_mwh or b.full_charge_capacity_mwh is None:
        return _unsupported(
            "AGENT_BATTERY", "Windows no reporta la capacidad de la batería", report, "battery"
        )
    wear = max(0.0, round(100 - 100 * b.full_charge_capacity_mwh / b.design_capacity_mwh, 1))
    text = (
        f"Desgaste {wear} % (capacidad {b.full_charge_capacity_mwh} de "
        f"{b.design_capacity_mwh} mWh)" + (f", {b.cycle_count} ciclos" if b.cycle_count else "")
    )
    if wear >= c.BATTERY_WEAR_FAIL:
        result = Result.FAIL
    elif wear >= c.BATTERY_WEAR_WARNING:
        result = Result.WARNING
    else:
        result = Result.OK
    return Evaluation(
        "AGENT_BATTERY", result, text, {**b.model_dump(exclude_none=True), "wear_percent": wear}
    )


def _stability(report: AgentReport) -> Evaluation:
    s = report.stability
    if s is None:
        return _unsupported(
            "AGENT_STABILITY", "No se pudo leer el registro de eventos", report, "stability"
        )
    text = (
        f"{s.bugchecks_30d} pantallazo(s) azul(es) y {s.unexpected_shutdowns_30d} apagado(s) "
        "inesperado(s) en 30 días"
    )
    if s.bugchecks_30d >= c.BUGCHECKS_FAIL:
        result = Result.FAIL
    elif (
        s.bugchecks_30d >= c.BUGCHECKS_WARNING
        or s.unexpected_shutdowns_30d >= c.UNEXPECTED_SHUTDOWNS_WARNING
    ):
        result = Result.WARNING
    else:
        result = Result.OK
    return Evaluation("AGENT_STABILITY", result, text, s.model_dump())
