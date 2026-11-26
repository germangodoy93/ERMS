import { http } from "@/services/http";
import type {
  NoticeKind,
  NoticePanel,
  NoticeTemplates,
  PendingNotice,
  PreparedNotice,
} from "@/types/api";

export async function getNoticePanel(orderId: string): Promise<NoticePanel> {
  return (await http.get<NoticePanel>(`/work-orders/${orderId}/notices`)).data;
}

export async function prepareNotice(
  orderId: string,
  kind: NoticeKind,
  body: string,
): Promise<PreparedNotice> {
  return (await http.post<PreparedNotice>(`/work-orders/${orderId}/notices`, { kind, body })).data;
}

export async function getPendingNotices(): Promise<PendingNotice[]> {
  return (await http.get<PendingNotice[]>("/notices/pending")).data;
}

export async function getNoticeTemplates(): Promise<NoticeTemplates> {
  return (await http.get<NoticeTemplates>("/notices/templates")).data;
}

export async function saveNoticeTemplate(kind: NoticeKind, body: string): Promise<NoticeTemplates> {
  return (await http.put<NoticeTemplates>(`/notices/templates/${kind}`, { body })).data;
}

export async function resetNoticeTemplate(kind: NoticeKind): Promise<NoticeTemplates> {
  return (await http.delete<NoticeTemplates>(`/notices/templates/${kind}`)).data;
}
