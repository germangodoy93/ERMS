import { http } from "@/services/http";
import type {
  ConsentChange,
  ConsentChannel,
  ConsentRecord,
  Customer,
  CustomerCreate,
  CustomerListItem,
  CustomerUpdate,
  Page,
} from "@/types/api";

export interface CustomerFilters {
  page: number;
  size: number;
  q?: string;
  is_active?: boolean;
}

export async function listCustomers(filters: CustomerFilters): Promise<Page<CustomerListItem>> {
  const params = Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== undefined && value !== ""),
  );
  const { data } = await http.get<Page<CustomerListItem>>("/customers", { params });
  return data;
}

export async function getCustomer(id: string): Promise<Customer> {
  const { data } = await http.get<Customer>(`/customers/${id}`);
  return data;
}

export async function createCustomer(payload: CustomerCreate): Promise<Customer> {
  const { data } = await http.post<Customer>("/customers", payload);
  return data;
}

export async function updateCustomer(id: string, payload: CustomerUpdate): Promise<Customer> {
  const { data } = await http.patch<Customer>(`/customers/${id}`, payload);
  return data;
}

export async function listConsents(id: string): Promise<ConsentRecord[]> {
  const { data } = await http.get<ConsentRecord[]>(`/customers/${id}/consents`);
  return data;
}

export async function changeConsent(id: string, payload: ConsentChange): Promise<Customer> {
  const { data } = await http.post<Customer>(`/customers/${id}/consents`, payload);
  return data;
}

export async function anonymizeCustomer(id: string, channel: ConsentChannel): Promise<Customer> {
  const { data } = await http.post<Customer>(`/customers/${id}/anonymize`, { channel });
  return data;
}
