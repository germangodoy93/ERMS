import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { ClaimCreate, ReportKind } from "@/types/api";

import { decideClaim, getDashboard, getReport, getWarranty, openClaim } from "./api";

export function useDashboard() {
  return useQuery({ queryKey: ["dashboard"], queryFn: getDashboard, refetchInterval: 60_000 });
}

export function useReport(kind: ReportKind, from: string, to: string, enabled: boolean) {
  return useQuery({
    queryKey: ["reports", kind, from, to],
    queryFn: () => getReport(kind, from, to),
    enabled,
    placeholderData: keepPreviousData,
  });
}

export const warrantyKey = (orderId: string) => ["work-orders", "warranty", orderId] as const;

export function useWarranty(orderId: string) {
  return useQuery({ queryKey: warrantyKey(orderId), queryFn: () => getWarranty(orderId) });
}

export function useOpenClaim(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ClaimCreate) => openClaim(orderId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["work-orders"] }),
  });
}

export function useDecideClaim(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      claimId,
      accepted,
      resolution,
    }: {
      claimId: string;
      accepted: boolean;
      resolution: string;
    }) => decideClaim(orderId, claimId, accepted, resolution),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: warrantyKey(orderId) }),
  });
}
