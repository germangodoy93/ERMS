import { http } from "@/services/http";
import type {
  Device,
  DeviceCategory,
  DeviceCreate,
  DeviceModel,
  DeviceModelCreate,
  DeviceModelUpdate,
  DeviceSearchItem,
  DeviceUpdate,
  Manufacturer,
  ManufacturerUpdate,
  Page,
} from "@/types/api";

export async function listCategories(): Promise<DeviceCategory[]> {
  const { data } = await http.get<DeviceCategory[]>("/catalog/categories");
  return data;
}

export async function listManufacturers(includeInactive = false): Promise<Manufacturer[]> {
  const { data } = await http.get<Manufacturer[]>("/catalog/manufacturers", {
    params: includeInactive ? { include_inactive: true } : undefined,
  });
  return data;
}

export async function createManufacturer(name: string): Promise<Manufacturer> {
  const { data } = await http.post<Manufacturer>("/catalog/manufacturers", { name });
  return data;
}

export async function updateManufacturer(
  id: string,
  payload: ManufacturerUpdate,
): Promise<Manufacturer> {
  const { data } = await http.patch<Manufacturer>(`/catalog/manufacturers/${id}`, payload);
  return data;
}

export interface ModelFilters {
  manufacturer_id?: string;
  category?: string;
  q?: string;
  include_inactive?: boolean;
}

export async function listModels(filters: ModelFilters): Promise<DeviceModel[]> {
  const params = Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== undefined && value !== ""),
  );
  const { data } = await http.get<DeviceModel[]>("/catalog/models", { params });
  return data;
}

export async function createModel(payload: DeviceModelCreate): Promise<DeviceModel> {
  const { data } = await http.post<DeviceModel>("/catalog/models", payload);
  return data;
}

export async function updateModel(id: string, payload: DeviceModelUpdate): Promise<DeviceModel> {
  const { data } = await http.patch<DeviceModel>(`/catalog/models/${id}`, payload);
  return data;
}

export async function listCustomerDevices(customerId: string): Promise<Device[]> {
  const { data } = await http.get<Device[]>(`/customers/${customerId}/devices`);
  return data;
}

export async function createDevice(customerId: string, payload: DeviceCreate): Promise<Device> {
  const { data } = await http.post<Device>(`/customers/${customerId}/devices`, payload);
  return data;
}

export async function updateDevice(id: string, payload: DeviceUpdate): Promise<Device> {
  const { data } = await http.patch<Device>(`/devices/${id}`, payload);
  return data;
}

export async function searchDevices(
  q: string,
  page: number,
  size: number,
): Promise<Page<DeviceSearchItem>> {
  const { data } = await http.get<Page<DeviceSearchItem>>("/devices", {
    params: { q, page, size },
  });
  return data;
}
