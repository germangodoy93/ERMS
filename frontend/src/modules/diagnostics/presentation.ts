import type { Diagnostic, DiagnosticResultCode } from "@/types/api";

export const RESULT_LABELS: Record<DiagnosticResultCode, string> = {
  OK: "Bien",
  WARNING: "Advertencia",
  FAIL: "Falla",
  NOT_TESTED: "No probado",
  NOT_SUPPORTED: "No soportado",
};

export const MANUAL_OPTIONS: DiagnosticResultCode[] = [
  "OK",
  "WARNING",
  "FAIL",
  "NOT_TESTED",
  "NOT_SUPPORTED",
];

export const RESULT_TONE: Record<DiagnosticResultCode, string> = {
  OK: "border-success/40 bg-success/10 text-success",
  WARNING: "border-warning/50 bg-warning/15 text-foreground",
  FAIL: "border-destructive/40 bg-destructive/10 text-destructive",
  NOT_TESTED: "border-border bg-muted text-muted-foreground",
  NOT_SUPPORTED: "border-border bg-muted text-muted-foreground",
};

/** Manual tests without a result: the backend refuses to close until all have one. */
export function pendingManualTests(diagnostic: Diagnostic): string[] {
  return diagnostic.results.filter((r) => !r.automated && r.result === null).map((r) => r.name);
}

export interface ResultCounts {
  ok: number;
  warning: number;
  fail: number;
  pending: number;
}

export function countResults(diagnostic: Diagnostic): ResultCounts {
  const counts: ResultCounts = { ok: 0, warning: 0, fail: 0, pending: 0 };
  for (const r of diagnostic.results) {
    if (r.result === "OK") counts.ok += 1;
    else if (r.result === "WARNING") counts.warning += 1;
    else if (r.result === "FAIL") counts.fail += 1;
    else if (r.result === null && !r.automated) counts.pending += 1;
  }
  return counts;
}

/** "28:41" until the pairing code expires; "vencido" after. */
export function remaining(expiresAt: string, now: number): string {
  const seconds = Math.max(0, Math.floor((new Date(expiresAt).getTime() - now) / 1000));
  if (seconds === 0) return "vencido";
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}
