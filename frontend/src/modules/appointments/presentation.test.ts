import type { AppointmentRead } from "@/types/api";

import {
  addDays,
  bogotaDate,
  bogotaTime,
  durationLabel,
  formatDayTitle,
  groupByDay,
  hoursLabel,
  toBogotaIso,
  weekdayOf,
  weekStart,
} from "./presentation";
import { appointmentSchema, fieldServiceSchema } from "./schemas";

describe("agenda dates", () => {
  it("moves through days and weeks starting on Monday", () => {
    expect(addDays("2026-11-30", 1)).toBe("2026-12-01");
    expect(addDays("2026-03-01", -1)).toBe("2026-02-28");
    expect(weekdayOf("2026-11-30")).toBe(0);
    expect(weekdayOf("2026-12-06")).toBe(6);
    expect(weekStart("2026-12-06")).toBe("2026-11-30");
    expect(weekStart("2026-11-30")).toBe("2026-11-30");
  });

  it("reads timestamps in Bogotá time", () => {
    expect(bogotaDate("2026-12-01T03:00:00Z")).toBe("2026-11-30");
    expect(bogotaTime("2026-11-30T13:30:00Z")).toBe("08:30");
    expect(toBogotaIso("2026-11-30", "09:30")).toBe("2026-11-30T09:30:00-05:00");
    expect(bogotaTime(new Date(toBogotaIso("2026-11-30", "17:45")).toISOString())).toBe("17:45");
  });

  it("labels days, hours and durations", () => {
    expect(formatDayTitle("2026-11-30")).toMatch(/^Lunes,? 30/);
    expect(hoursLabel({ weekday: 0, opens: "08:00:00", closes: "18:00:00" })).toBe("8:00 a 18:00");
    expect(hoursLabel({ weekday: 6, opens: null, closes: null })).toBe("Sin servicio");
    expect(durationLabel(30)).toBe("30 min");
    expect(durationLabel(60)).toBe("1 h");
    expect(durationLabel(90)).toBe("1 h 30 min");
  });

  it("groups appointments by Bogotá day in time order", () => {
    const at = (id: string, starts_at: string) => ({ id, starts_at }) as AppointmentRead;
    const groups = groupByDay(
      [
        at("b", "2026-11-30T20:00:00Z"),
        at("a", "2026-11-30T13:00:00Z"),
        at("c", "2026-12-01T04:00:00Z"),
      ],
      ["2026-11-30", "2026-12-01"],
    );
    expect(groups.get("2026-11-30")?.map((a) => a.id)).toEqual(["a", "b", "c"]);
    expect(groups.get("2026-12-01")).toEqual([]);
  });
});

describe("agenda forms", () => {
  const base = {
    service_id: "s1",
    date: "2026-11-30",
    time: "09:00",
    duration: "60",
    technician_id: "",
    reason: "No enciende el computador.",
    address: "",
    locality: "",
    notes: "",
    consent_channel: "",
  };
  const issues = (modality: "ON_SITE" | "REMOTE", values: Partial<typeof base>) => {
    const result = appointmentSchema(() => modality).safeParse({ ...base, ...values });
    return result.success ? [] : result.error.issues.map((i) => i.path.join("."));
  };

  it("asks for the address on site and the authorization when remote", () => {
    expect(issues("ON_SITE", {})).toEqual(["address", "locality"]);
    expect(issues("ON_SITE", { address: "Calle 1 # 2-3", locality: "Suba" })).toEqual([]);
    expect(issues("REMOTE", {})).toEqual(["consent_channel"]);
    expect(issues("REMOTE", { consent_channel: "VERBAL" })).toEqual([]);
    expect(issues("REMOTE", { consent_channel: "VERBAL", duration: "7" })).toContain("duration");
    expect(issues("REMOTE", { consent_channel: "VERBAL", duration: "62" })).toContain("duration");
  });

  it("validates the service catalog form", () => {
    const service = {
      name: "Visita técnica",
      modality: "ON_SITE",
      duration_minutes: "60",
      price: "",
      tax_rate: "0",
      price_includes_tax: false,
      description: "",
      is_active: true,
    };
    expect(fieldServiceSchema.safeParse(service).success).toBe(true);
    expect(fieldServiceSchema.safeParse({ ...service, price: "80.000" }).success).toBe(true);
    expect(fieldServiceSchema.safeParse({ ...service, price: "ochenta" }).success).toBe(false);
  });
});
