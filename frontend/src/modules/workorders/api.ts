import { http } from "@/services/http";
import type {
  CurrentReceptionTerms,
  DeliveryRequest,
  Page,
  PersonRef,
  Photo,
  PhotoList,
  ReceptionTerms,
  WorkOrder,
  WorkOrderCreate,
  WorkOrderListItem,
  WorkOrderStatus,
  WorkOrderUpdate,
} from "@/types/api";

export interface WorkOrderFilters {
  page: number;
  size: number;
  q?: string;
  status?: WorkOrderStatus[];
  technician_id?: string;
  unassigned?: boolean;
  open?: boolean;
}

export async function listWorkOrders(filters: WorkOrderFilters): Promise<Page<WorkOrderListItem>> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === "" || value === false) continue;
    if (Array.isArray(value)) value.forEach((v) => params.append(key, String(v)));
    else params.append(key, String(value));
  }
  const { data } = await http.get<Page<WorkOrderListItem>>("/work-orders", { params });
  return data;
}

export async function getWorkOrder(id: string): Promise<WorkOrder> {
  const { data } = await http.get<WorkOrder>(`/work-orders/${id}`);
  return data;
}

export async function createWorkOrder(payload: WorkOrderCreate): Promise<WorkOrder> {
  const { data } = await http.post<WorkOrder>("/work-orders", payload);
  return data;
}

export async function updateWorkOrder(id: string, payload: WorkOrderUpdate): Promise<WorkOrder> {
  const { data } = await http.patch<WorkOrder>(`/work-orders/${id}`, payload);
  return data;
}

export async function changeStatus(
  id: string,
  status: WorkOrderStatus,
  reason: string | null,
): Promise<WorkOrder> {
  const { data } = await http.post<WorkOrder>(`/work-orders/${id}/status`, { status, reason });
  return data;
}

export async function deliverWorkOrder(id: string, payload: DeliveryRequest): Promise<WorkOrder> {
  const { data } = await http.post<WorkOrder>(`/work-orders/${id}/delivery`, payload);
  return data;
}

export async function assignTechnician(
  id: string,
  technicianId: string | null,
): Promise<WorkOrder> {
  const { data } = await http.put<WorkOrder>(`/work-orders/${id}/assignment`, {
    technician_id: technicianId,
  });
  return data;
}

export async function listTechnicians(): Promise<PersonRef[]> {
  const { data } = await http.get<PersonRef[]>("/work-orders/technicians");
  return data;
}

export async function downloadReceptionAct(id: string): Promise<Blob> {
  const { data } = await http.get<Blob>(`/work-orders/${id}/reception-act.pdf`, {
    responseType: "blob",
  });
  return data;
}

export async function listPhotos(id: string): Promise<PhotoList> {
  const { data } = await http.get<PhotoList>(`/work-orders/${id}/photos`);
  return data;
}

export async function uploadPhoto(id: string, file: File): Promise<Photo> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await http.post<Photo>(`/work-orders/${id}/photos`, form);
  return data;
}

export async function getPhotoContent(orderId: string, photoId: string): Promise<Blob> {
  const { data } = await http.get<Blob>(`/work-orders/${orderId}/photos/${photoId}`, {
    responseType: "blob",
  });
  return data;
}

export async function deletePhoto(orderId: string, photoId: string): Promise<void> {
  await http.delete(`/work-orders/${orderId}/photos/${photoId}`);
}

export async function getReceptionTerms(): Promise<CurrentReceptionTerms> {
  const { data } = await http.get<CurrentReceptionTerms>("/reception-terms");
  return data;
}

export async function publishReceptionTerms(content: string): Promise<ReceptionTerms> {
  const { data } = await http.post<ReceptionTerms>("/reception-terms", { content });
  return data;
}
