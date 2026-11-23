import { http } from "@/services/http";
import type {
  AssemblyChecklist,
  BuildRead,
  BuildSummary,
  BuildWrite,
  CatalogImportItem,
  CatalogImportResult,
  CatalogPart,
  EvaluateRequest,
  Evaluation,
  WorkOrder,
} from "@/types/api";

export async function getCatalog(): Promise<CatalogPart[]> {
  const { data } = await http.get<CatalogPart[]>("/assembly/catalog");
  return data;
}

export async function importCatalog(items: CatalogImportItem[]): Promise<CatalogImportResult> {
  const { data } = await http.post<CatalogImportResult>("/assembly/catalog/import", { items });
  return data;
}

export async function evaluateBuild(payload: EvaluateRequest): Promise<Evaluation> {
  const { data } = await http.post<Evaluation>("/assembly/evaluate", payload);
  return data;
}

export async function listBuilds(): Promise<BuildSummary[]> {
  const { data } = await http.get<BuildSummary[]>("/assembly/builds");
  return data;
}

export async function getBuild(id: string): Promise<BuildRead> {
  const { data } = await http.get<BuildRead>(`/assembly/builds/${id}`);
  return data;
}

export async function saveBuild(payload: BuildWrite, id?: string): Promise<BuildRead> {
  const { data } = id
    ? await http.put<BuildRead>(`/assembly/builds/${id}`, payload)
    : await http.post<BuildRead>("/assembly/builds", payload);
  return data;
}

export async function deleteBuild(id: string): Promise<void> {
  await http.delete(`/assembly/builds/${id}`);
}

export async function orderBuild(id: string, customerId: string): Promise<WorkOrder> {
  const { data } = await http.post<WorkOrder>(`/assembly/builds/${id}/order`, {
    customer_id: customerId,
  });
  return data;
}

export async function getChecklist(orderId: string): Promise<AssemblyChecklist> {
  const { data } = await http.get<AssemblyChecklist>(`/work-orders/${orderId}/assembly`);
  return data;
}

export async function consumeParts(orderId: string): Promise<AssemblyChecklist> {
  const { data } = await http.post<AssemblyChecklist>(`/work-orders/${orderId}/assembly/consume`);
  return data;
}

export async function completeStep(orderId: string, code: string): Promise<AssemblyChecklist> {
  const { data } = await http.post<AssemblyChecklist>(
    `/work-orders/${orderId}/assembly/steps/${code}`,
  );
  return data;
}
