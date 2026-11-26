import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { NoticeKind } from "@/types/api";

import {
  getNoticePanel,
  getNoticeTemplates,
  getPendingNotices,
  prepareNotice,
  resetNoticeTemplate,
  saveNoticeTemplate,
} from "./api";

// Under "work-orders" and "dashboard" so they refresh whenever an order changes.
export const noticeKeys = {
  panel: (orderId: string) => ["work-orders", "notices", orderId] as const,
  pending: ["dashboard", "notices-pending"] as const,
  templates: ["notices", "templates"] as const,
};

export function useNoticePanel(orderId: string) {
  return useQuery({ queryKey: noticeKeys.panel(orderId), queryFn: () => getNoticePanel(orderId) });
}

export function usePrepareNotice(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ kind, body }: { kind: NoticeKind; body: string }) =>
      prepareNotice(orderId, kind, body),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: noticeKeys.panel(orderId) }),
        queryClient.invalidateQueries({ queryKey: noticeKeys.pending }),
      ]),
  });
}

export function usePendingNotices(enabled: boolean) {
  return useQuery({ queryKey: noticeKeys.pending, queryFn: getPendingNotices, enabled });
}

export function useNoticeTemplates() {
  return useQuery({ queryKey: noticeKeys.templates, queryFn: getNoticeTemplates });
}

export function useSaveNoticeTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ kind, body }: { kind: NoticeKind; body: string | null }) =>
      body === null ? resetNoticeTemplate(kind) : saveNoticeTemplate(kind, body),
    onSuccess: (data) => {
      queryClient.setQueryData(noticeKeys.templates, data);
      return queryClient.invalidateQueries({ queryKey: ["work-orders", "notices"] });
    },
  });
}
