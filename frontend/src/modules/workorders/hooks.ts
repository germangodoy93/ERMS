import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  DeliveryRequest,
  WorkOrder,
  WorkOrderCreate,
  WorkOrderStatus,
  WorkOrderUpdate,
} from "@/types/api";

import {
  assignTechnician,
  changeStatus,
  createWorkOrder,
  deletePhoto,
  deliverWorkOrder,
  getReceptionTerms,
  getWorkOrder,
  listPhotos,
  listTechnicians,
  listWorkOrders,
  publishReceptionTerms,
  updateWorkOrder,
  uploadPhoto,
  type WorkOrderFilters,
} from "./api";

export const workOrderKeys = {
  all: ["work-orders"] as const,
  list: (filters: WorkOrderFilters) => ["work-orders", "list", filters] as const,
  detail: (id: string) => ["work-orders", "detail", id] as const,
  photos: (id: string) => ["work-orders", "photos", id] as const,
  technicians: ["work-orders", "technicians"] as const,
};
export const termsKey = ["reception-terms"] as const;

export function useWorkOrders(filters: WorkOrderFilters) {
  return useQuery({
    queryKey: workOrderKeys.list(filters),
    queryFn: () => listWorkOrders(filters),
    placeholderData: keepPreviousData,
  });
}

export function useWorkOrder(id: string) {
  return useQuery({ queryKey: workOrderKeys.detail(id), queryFn: () => getWorkOrder(id) });
}

export function useTechnicians(enabled: boolean) {
  return useQuery({
    queryKey: workOrderKeys.technicians,
    queryFn: listTechnicians,
    enabled,
    staleTime: 60_000,
  });
}

export function useReceptionTerms() {
  return useQuery({ queryKey: termsKey, queryFn: getReceptionTerms, staleTime: 60_000 });
}

export function usePublishReceptionTerms() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (content: string) => publishReceptionTerms(content),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: termsKey }),
  });
}

/** Store the returned order as the detail and refresh every list. */
function useOnOrderSaved() {
  const queryClient = useQueryClient();
  return async (order: WorkOrder) => {
    queryClient.setQueryData(workOrderKeys.detail(order.id), order);
    await queryClient.invalidateQueries({ queryKey: ["work-orders", "list"] });
  };
}

export function useCreateWorkOrder() {
  const onSaved = useOnOrderSaved();
  return useMutation({
    mutationFn: (payload: WorkOrderCreate) => createWorkOrder(payload),
    onSuccess: onSaved,
  });
}

export function useUpdateWorkOrder() {
  const onSaved = useOnOrderSaved();
  return useMutation({
    mutationFn: ({ id, changes }: { id: string; changes: WorkOrderUpdate }) =>
      updateWorkOrder(id, changes),
    onSuccess: onSaved,
  });
}

export function useChangeStatus() {
  const onSaved = useOnOrderSaved();
  return useMutation({
    mutationFn: ({
      id,
      status,
      reason,
    }: {
      id: string;
      status: WorkOrderStatus;
      reason: string | null;
    }) => changeStatus(id, status, reason),
    onSuccess: onSaved,
  });
}

export function useDeliver() {
  const onSaved = useOnOrderSaved();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: DeliveryRequest }) =>
      deliverWorkOrder(id, payload),
    onSuccess: onSaved,
  });
}

export function useAssign() {
  const onSaved = useOnOrderSaved();
  return useMutation({
    mutationFn: ({ id, technicianId }: { id: string; technicianId: string | null }) =>
      assignTechnician(id, technicianId),
    onSuccess: onSaved,
  });
}

export function usePhotos(orderId: string) {
  return useQuery({ queryKey: workOrderKeys.photos(orderId), queryFn: () => listPhotos(orderId) });
}

export function useUploadPhoto(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadPhoto(orderId, file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: workOrderKeys.photos(orderId) }),
  });
}

export function useDeletePhoto(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (photoId: string) => deletePhoto(orderId, photoId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: workOrderKeys.photos(orderId) }),
  });
}
