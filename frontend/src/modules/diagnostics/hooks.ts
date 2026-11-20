import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { workOrderKeys } from "@/modules/workorders/hooks";
import type { Diagnostic, DiagnosticResultInput } from "@/types/api";

import {
  closeDiagnostic,
  createAgentPairing,
  getDiagnostic,
  reopenDiagnostic,
  saveResults,
} from "./api";

export const diagnosticKey = (orderId: string) => ["work-orders", "diagnostic", orderId] as const;

export function useDiagnostic(orderId: string, options: { pollMs?: number } = {}) {
  return useQuery({
    queryKey: diagnosticKey(orderId),
    queryFn: () => getDiagnostic(orderId),
    refetchInterval: options.pollMs,
  });
}

/** Store the new diagnostic and refresh the order (its allowed transitions may change). */
function useOnSaved(orderId: string) {
  const queryClient = useQueryClient();
  return async (diagnostic: Diagnostic) => {
    queryClient.setQueryData(diagnosticKey(orderId), diagnostic);
    await queryClient.invalidateQueries({ queryKey: workOrderKeys.detail(orderId) });
  };
}

export function useSaveResults(orderId: string) {
  const onSaved = useOnSaved(orderId);
  return useMutation({
    mutationFn: (results: DiagnosticResultInput[]) => saveResults(orderId, results),
    onSuccess: onSaved,
  });
}

export function useCloseDiagnostic(orderId: string) {
  const onSaved = useOnSaved(orderId);
  return useMutation({
    mutationFn: ({
      conclusion,
      recommendation,
    }: {
      conclusion: string;
      recommendation: string | null;
    }) => closeDiagnostic(orderId, conclusion, recommendation),
    onSuccess: onSaved,
  });
}

export function useReopenDiagnostic(orderId: string) {
  const onSaved = useOnSaved(orderId);
  return useMutation({ mutationFn: () => reopenDiagnostic(orderId), onSuccess: onSaved });
}

export function useCreatePairing(orderId: string) {
  return useMutation({ mutationFn: () => createAgentPairing(orderId) });
}
