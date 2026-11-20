import { http } from "@/services/http";
import type {
  ClaimCreate,
  Dashboard,
  Report,
  ReportKind,
  WarrantyClaim,
  WarrantyOverview,
  WorkOrder,
} from "@/types/api";

export async function getDashboard(): Promise<Dashboard> {
  const { data } = await http.get<Dashboard>("/dashboard");
  return data;
}

export async function getReport(kind: ReportKind, from: string, to: string): Promise<Report> {
  const { data } = await http.get<Report>(`/reports/${kind}`, { params: { from, to } });
  return data;
}

export async function downloadReport(
  kind: ReportKind,
  from: string,
  to: string,
  format: "csv" | "pdf",
): Promise<Blob> {
  const { data } = await http.get<Blob>(`/reports/${kind}`, {
    params: { from, to, format },
    responseType: "blob",
  });
  return data;
}

export async function getWarranty(orderId: string): Promise<WarrantyOverview> {
  const { data } = await http.get<WarrantyOverview>(`/work-orders/${orderId}/warranty`);
  return data;
}

export async function openClaim(orderId: string, payload: ClaimCreate): Promise<WorkOrder> {
  const { data } = await http.post<WorkOrder>(`/work-orders/${orderId}/warranty/claims`, payload);
  return data;
}

export async function decideClaim(
  orderId: string,
  claimId: string,
  accepted: boolean,
  resolution: string,
): Promise<WarrantyClaim> {
  const { data } = await http.post<WarrantyClaim>(
    `/work-orders/${orderId}/warranty/claims/${claimId}/decision`,
    { accepted, resolution },
  );
  return data;
}
