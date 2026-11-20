import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { inventoryKeys } from "@/modules/inventory/hooks";
import type {
  ConsentChannel,
  DiagnosticResultInput,
  PaymentMethod,
  QuoteItemInput,
} from "@/types/api";

import {
  addQualityCheck,
  addTask,
  consumePart,
  createQuote,
  discardQuote,
  getBilling,
  getQuotes,
  getRepair,
  registerPayment,
  respondQuote,
  returnPart,
  saveQuote,
  sendQuote,
} from "./api";

export const workshopKeys = {
  quotes: (orderId: string) => ["work-orders", "quotes", orderId] as const,
  repair: (orderId: string) => ["work-orders", "repair", orderId] as const,
  billing: (orderId: string) => ["work-orders", "billing", orderId] as const,
};

export function useQuotes(orderId: string) {
  return useQuery({ queryKey: workshopKeys.quotes(orderId), queryFn: () => getQuotes(orderId) });
}

export function useRepair(orderId: string) {
  return useQuery({ queryKey: workshopKeys.repair(orderId), queryFn: () => getRepair(orderId) });
}

export function useBilling(orderId: string) {
  return useQuery({ queryKey: workshopKeys.billing(orderId), queryFn: () => getBilling(orderId) });
}

/** Any workshop change may affect the order, its quotes, repair, billing and stock. */
function useRefreshOrder(orderId: string) {
  const queryClient = useQueryClient();
  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["work-orders", "detail", orderId] }),
      queryClient.invalidateQueries({ queryKey: workshopKeys.quotes(orderId) }),
      queryClient.invalidateQueries({ queryKey: workshopKeys.repair(orderId) }),
      queryClient.invalidateQueries({ queryKey: workshopKeys.billing(orderId) }),
      queryClient.invalidateQueries({ queryKey: ["work-orders", "list"] }),
      queryClient.invalidateQueries({ queryKey: inventoryKeys.all }),
    ]);
  };
}

export function useQuoteActions(orderId: string) {
  const onSuccess = useRefreshOrder(orderId);
  return {
    create: useMutation({ mutationFn: () => createQuote(orderId), onSuccess }),
    save: useMutation({
      mutationFn: ({
        quoteId,
        items,
        notes,
      }: {
        quoteId: string;
        items: QuoteItemInput[];
        notes: string | null;
      }) => saveQuote(orderId, quoteId, items, notes),
      onSuccess,
    }),
    discard: useMutation({
      mutationFn: (quoteId: string) => discardQuote(orderId, quoteId),
      onSuccess,
    }),
    send: useMutation({ mutationFn: (quoteId: string) => sendQuote(orderId, quoteId), onSuccess }),
    respond: useMutation({
      mutationFn: ({
        quoteId,
        accepted,
        channel,
        reason,
      }: {
        quoteId: string;
        accepted: boolean;
        channel: ConsentChannel;
        reason: string | null;
      }) => respondQuote(orderId, quoteId, accepted, channel, reason),
      onSuccess,
    }),
  };
}

export function useRepairActions(orderId: string) {
  const onSuccess = useRefreshOrder(orderId);
  return {
    addTask: useMutation({
      mutationFn: ({ description, minutes }: { description: string; minutes: number | null }) =>
        addTask(orderId, description, minutes),
      onSuccess,
    }),
    consume: useMutation({
      mutationFn: ({
        taskId,
        partId,
        quantity,
      }: {
        taskId: string;
        partId: string;
        quantity: number;
      }) => consumePart(orderId, taskId, partId, quantity),
      onSuccess,
    }),
    returnPart: useMutation({
      mutationFn: ({ taskId, repairPartId }: { taskId: string; repairPartId: string }) =>
        returnPart(orderId, taskId, repairPartId),
      onSuccess,
    }),
    qualityCheck: useMutation({
      mutationFn: ({
        results,
        notes,
      }: {
        results: DiagnosticResultInput[];
        notes: string | null;
      }) => addQualityCheck(orderId, results, notes),
      onSuccess,
    }),
  };
}

export function useRegisterPayment(orderId: string) {
  const onSuccess = useRefreshOrder(orderId);
  return useMutation({
    mutationFn: ({
      amount,
      method,
      reference,
    }: {
      amount: string;
      method: PaymentMethod;
      reference: string | null;
    }) => registerPayment(orderId, amount, method, reference),
    onSuccess,
  });
}
