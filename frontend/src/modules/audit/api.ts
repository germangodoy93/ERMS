import { http } from "@/services/http";
import type { AuditLog, Page } from "@/types/api";

export interface AuditFilters {
  page: number;
  size: number;
  action?: string;
  date_from?: string;
  date_to?: string;
}

export async function listAuditLogs(filters: AuditFilters): Promise<Page<AuditLog>> {
  const params = Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== undefined && value !== ""),
  );
  const { data } = await http.get<Page<AuditLog>>("/audit-logs", { params });
  return data;
}
