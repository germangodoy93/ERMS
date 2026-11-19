import { COMPONENT_STATUSES } from "@/types/api";

import {
  COMPONENT_STATUS_PRESENTATION,
  componentLabel,
  environmentLabel,
  formatBogotaDateTime,
  formatLatency,
} from "./presentation";

describe("system presentation", () => {
  it("has a presentation for every component status", () => {
    for (const status of COMPONENT_STATUSES) {
      expect(COMPONENT_STATUS_PRESENTATION[status].label).toBeTruthy();
    }
  });

  it("translates known components and passes unknown names through", () => {
    expect(componentLabel("database")).toBe("Base de datos (PostgreSQL)");
    expect(componentLabel("storage")).toBe("storage");
  });

  it("translates environments", () => {
    expect(environmentLabel("production")).toBe("Producción");
  });

  it("formats UTC timestamps in Bogotá time (UTC-5)", () => {
    expect(formatBogotaDateTime("2026-11-19T17:30:00Z")).toMatch(/12:30:00/);
  });

  it("formats latency only when present", () => {
    expect(formatLatency(null)).toBeNull();
    expect(formatLatency(3.25)).toMatch(/ms$/);
  });
});
