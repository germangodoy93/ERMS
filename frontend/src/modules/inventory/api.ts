import { http } from "@/services/http";
import type {
  Movement,
  PartItem,
  PartWrite,
  StockEntry,
  StockEntryCreate,
  Supplier,
  SupplierWrite,
} from "@/types/api";

export interface PartFilters {
  q?: string;
  low_stock?: boolean;
  include_inactive?: boolean;
}

export async function listParts(filters: PartFilters): Promise<PartItem[]> {
  const params = Object.fromEntries(
    Object.entries(filters).filter(([, v]) => v !== undefined && v !== "" && v !== false),
  );
  const { data } = await http.get<PartItem[]>("/inventory/parts", { params });
  return data;
}

export async function savePart(payload: PartWrite, id?: string): Promise<PartItem> {
  const { data } = id
    ? await http.put<PartItem>(`/inventory/parts/${id}`, payload)
    : await http.post<PartItem>("/inventory/parts", payload);
  return data;
}

export async function listMovements(partId: string): Promise<Movement[]> {
  const { data } = await http.get<Movement[]>(`/inventory/parts/${partId}/movements`);
  return data;
}

export async function adjustStock(
  partId: string,
  counted_quantity: number,
  reason: string,
): Promise<PartItem> {
  const { data } = await http.post<PartItem>(`/inventory/parts/${partId}/adjustments`, {
    counted_quantity,
    reason,
  });
  return data;
}

export async function receiveStock(payload: StockEntryCreate): Promise<StockEntry> {
  const { data } = await http.post<StockEntry>("/inventory/entries", payload);
  return data;
}

export async function listSuppliers(includeInactive = false): Promise<Supplier[]> {
  const { data } = await http.get<Supplier[]>("/inventory/suppliers", {
    params: includeInactive ? { include_inactive: true } : undefined,
  });
  return data;
}

export async function saveSupplier(payload: SupplierWrite, id?: string): Promise<Supplier> {
  const { data } = id
    ? await http.put<Supplier>(`/inventory/suppliers/${id}`, payload)
    : await http.post<Supplier>("/inventory/suppliers", payload);
  return data;
}
