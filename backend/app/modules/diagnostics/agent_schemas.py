"""Contract between the Windows agent and the API (agent → POST /diagnostics/agent/report).

Every section is optional: the agent sends only what Windows let it read and lists the rest
in `errors`. Sizes are bounded so a tampered agent cannot flood the database.
"""

from pydantic import BaseModel, ConfigDict, Field

Text = Field(default=None, max_length=200)


class _Section(BaseModel):
    model_config = ConfigDict(extra="ignore")


class SystemInfo(_Section):
    os_caption: str | None = Text
    os_version: str | None = Text
    os_build: str | None = Text
    architecture: str | None = Text
    manufacturer: str | None = Text
    model: str | None = Text
    bios_serial: str | None = Text
    bios_version: str | None = Text
    last_boot: str | None = Text


class CpuInfo(_Section):
    name: str | None = Text
    cores: int | None = Field(default=None, ge=0, le=4096)
    logical_processors: int | None = Field(default=None, ge=0, le=8192)
    max_clock_mhz: int | None = Field(default=None, ge=0, le=100_000)


class MemoryModule(_Section):
    capacity_bytes: int | None = Field(default=None, ge=0)
    speed_mhz: int | None = Field(default=None, ge=0, le=100_000)
    manufacturer: str | None = Text
    part_number: str | None = Text


class MemoryInfo(_Section):
    total_bytes: int | None = Field(default=None, ge=0)
    modules: list[MemoryModule] = Field(default_factory=list, max_length=32)


class GpuInfo(_Section):
    name: str | None = Text
    driver_version: str | None = Text
    adapter_ram_bytes: int | None = Field(default=None, ge=0)


class DiskInfo(_Section):
    friendly_name: str | None = Text
    media_type: str | None = Text
    bus_type: str | None = Text
    size_bytes: int | None = Field(default=None, ge=0)
    health_status: str | None = Text
    operational_status: str | None = Text


class VolumeInfo(_Section):
    drive_letter: str | None = Field(default=None, max_length=4)
    size_bytes: int | None = Field(default=None, ge=0)
    free_bytes: int | None = Field(default=None, ge=0)
    file_system: str | None = Field(default=None, max_length=20)


class SmartInfo(_Section):
    disk: str | None = Text
    temperature_c: int | None = Field(default=None, ge=-50, le=200)
    wear_percent: int | None = Field(default=None, ge=0, le=255)
    read_errors: int | None = Field(default=None, ge=0)
    write_errors: int | None = Field(default=None, ge=0)
    power_on_hours: int | None = Field(default=None, ge=0)


class BatteryInfo(_Section):
    present: bool
    design_capacity_mwh: int | None = Field(default=None, ge=0)
    full_charge_capacity_mwh: int | None = Field(default=None, ge=0)
    cycle_count: int | None = Field(default=None, ge=0)


class StabilityInfo(_Section):
    unexpected_shutdowns_30d: int = Field(ge=0)
    bugchecks_30d: int = Field(ge=0)


class AgentReport(_Section):
    agent_version: str = Field(max_length=20)
    elevated: bool = Field(description="True si el agente se ejecutó como administrador")
    system: SystemInfo | None = None
    cpus: list[CpuInfo] | None = Field(default=None, max_length=16)
    memory: MemoryInfo | None = None
    gpus: list[GpuInfo] | None = Field(default=None, max_length=8)
    disks: list[DiskInfo] | None = Field(default=None, max_length=32)
    volumes: list[VolumeInfo] | None = Field(default=None, max_length=32)
    smart: list[SmartInfo] | None = Field(default=None, max_length=32)
    battery: BatteryInfo | None = None
    stability: StabilityInfo | None = None
    errors: dict[str, str] = Field(default_factory=dict, max_length=20)


class PairRequest(BaseModel):
    code: str = Field(min_length=6, max_length=20)


class PairResponse(BaseModel):
    token: str
    expires_at: str
    work_order_number: str
    device: str


class ReportAccepted(BaseModel):
    results: int
