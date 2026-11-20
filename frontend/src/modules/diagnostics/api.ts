import { http } from "@/services/http";
import type { AgentPairing, Diagnostic, DiagnosticResultInput } from "@/types/api";

const base = (orderId: string) => `/work-orders/${orderId}/diagnostic`;

export async function getDiagnostic(orderId: string): Promise<Diagnostic> {
  const { data } = await http.get<Diagnostic>(base(orderId));
  return data;
}

export async function saveResults(
  orderId: string,
  results: DiagnosticResultInput[],
): Promise<Diagnostic> {
  const { data } = await http.put<Diagnostic>(`${base(orderId)}/results`, { results });
  return data;
}

export async function closeDiagnostic(
  orderId: string,
  conclusion: string,
  recommendation: string | null,
): Promise<Diagnostic> {
  const { data } = await http.post<Diagnostic>(`${base(orderId)}/close`, {
    conclusion,
    recommendation,
  });
  return data;
}

export async function reopenDiagnostic(orderId: string): Promise<Diagnostic> {
  const { data } = await http.post<Diagnostic>(`${base(orderId)}/reopen`);
  return data;
}

export async function createAgentPairing(orderId: string): Promise<AgentPairing> {
  const { data } = await http.post<AgentPairing>(`${base(orderId)}/agent-pairing`);
  return data;
}

export async function downloadDiagnosticReport(orderId: string): Promise<Blob> {
  const { data } = await http.get<Blob>(`/work-orders/${orderId}/diagnostic-report.pdf`, {
    responseType: "blob",
  });
  return data;
}
