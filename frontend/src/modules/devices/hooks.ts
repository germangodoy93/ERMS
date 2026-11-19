import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  DeviceCreate,
  DeviceModelCreate,
  DeviceModelUpdate,
  DeviceUpdate,
  ManufacturerUpdate,
} from "@/types/api";

import {
  createDevice,
  createManufacturer,
  createModel,
  listCategories,
  listCustomerDevices,
  listManufacturers,
  listModels,
  searchDevices,
  updateDevice,
  updateManufacturer,
  updateModel,
  type ModelFilters,
} from "./api";

export const catalogKeys = {
  all: ["catalog"] as const,
  categories: ["catalog", "categories"] as const,
  manufacturers: (includeInactive: boolean) =>
    ["catalog", "manufacturers", includeInactive] as const,
  models: (filters: ModelFilters) => ["catalog", "models", filters] as const,
};
export const deviceKeys = {
  all: ["devices"] as const,
  customer: (customerId: string) => ["devices", "customer", customerId] as const,
  search: (q: string, page: number) => ["devices", "search", q, page] as const,
};

export function useCategories() {
  return useQuery({
    queryKey: catalogKeys.categories,
    queryFn: listCategories,
    staleTime: Infinity,
  });
}

export function useManufacturers(includeInactive = false) {
  return useQuery({
    queryKey: catalogKeys.manufacturers(includeInactive),
    queryFn: () => listManufacturers(includeInactive),
    staleTime: 60_000,
  });
}

export function useModels(filters: ModelFilters, enabled = true) {
  return useQuery({
    queryKey: catalogKeys.models(filters),
    queryFn: () => listModels(filters),
    enabled,
    placeholderData: keepPreviousData,
  });
}

function useInvalidate(key: readonly string[]) {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: key });
}

export function useCreateManufacturer() {
  const invalidate = useInvalidate(catalogKeys.all);
  return useMutation({ mutationFn: createManufacturer, onSuccess: invalidate });
}

export function useUpdateManufacturer() {
  const invalidate = useInvalidate(catalogKeys.all);
  return useMutation({
    mutationFn: ({ id, changes }: { id: string; changes: ManufacturerUpdate }) =>
      updateManufacturer(id, changes),
    onSuccess: invalidate,
  });
}

export function useCreateModel() {
  const invalidate = useInvalidate(catalogKeys.all);
  return useMutation({
    mutationFn: (payload: DeviceModelCreate) => createModel(payload),
    onSuccess: invalidate,
  });
}

export function useUpdateModel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, changes }: { id: string; changes: DeviceModelUpdate }) =>
      updateModel(id, changes),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: catalogKeys.all });
      await queryClient.invalidateQueries({ queryKey: deviceKeys.all });
    },
  });
}

export function useCustomerDevices(customerId: string) {
  return useQuery({
    queryKey: deviceKeys.customer(customerId),
    queryFn: () => listCustomerDevices(customerId),
  });
}

export function useSearchDevices(q: string, page: number, size: number) {
  return useQuery({
    queryKey: deviceKeys.search(q, page),
    queryFn: () => searchDevices(q, page, size),
    enabled: q.length >= 3,
    placeholderData: keepPreviousData,
  });
}

export function useCreateDevice() {
  const invalidate = useInvalidate(deviceKeys.all);
  return useMutation({
    mutationFn: ({ customerId, payload }: { customerId: string; payload: DeviceCreate }) =>
      createDevice(customerId, payload),
    onSuccess: invalidate,
  });
}

export function useUpdateDevice() {
  const invalidate = useInvalidate(deviceKeys.all);
  return useMutation({
    mutationFn: ({ id, changes }: { id: string; changes: DeviceUpdate }) =>
      updateDevice(id, changes),
    onSuccess: invalidate,
  });
}
