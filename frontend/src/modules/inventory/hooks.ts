import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { PartWrite, StockEntryCreate, SupplierWrite } from "@/types/api";

import {
  adjustStock,
  listMovements,
  listParts,
  listSuppliers,
  receiveStock,
  savePart,
  saveSupplier,
  type PartFilters,
} from "./api";

export const inventoryKeys = {
  all: ["inventory"] as const,
  parts: (filters: PartFilters) => ["inventory", "parts", filters] as const,
  movements: (partId: string) => ["inventory", "movements", partId] as const,
  suppliers: ["inventory", "suppliers"] as const,
};

export function useParts(filters: PartFilters, enabled = true) {
  return useQuery({
    queryKey: inventoryKeys.parts(filters),
    queryFn: () => listParts(filters),
    placeholderData: keepPreviousData,
    enabled,
  });
}

export function useMovements(partId: string) {
  return useQuery({
    queryKey: inventoryKeys.movements(partId),
    queryFn: () => listMovements(partId),
  });
}

export function useSuppliers() {
  return useQuery({ queryKey: inventoryKeys.suppliers, queryFn: () => listSuppliers() });
}

function useInvalidateInventory() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: inventoryKeys.all });
}

export function useSavePart() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: ({ payload, id }: { payload: PartWrite; id?: string }) => savePart(payload, id),
    onSuccess: invalidate,
  });
}

export function useAdjustStock() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: ({
      partId,
      quantity,
      reason,
    }: {
      partId: string;
      quantity: number;
      reason: string;
    }) => adjustStock(partId, quantity, reason),
    onSuccess: invalidate,
  });
}

export function useReceiveStock() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (payload: StockEntryCreate) => receiveStock(payload),
    onSuccess: invalidate,
  });
}

export function useSaveSupplier() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: ({ payload, id }: { payload: SupplierWrite; id?: string }) =>
      saveSupplier(payload, id),
    onSuccess: invalidate,
  });
}
