import { http } from "@/services/http";
import type {
  Billing,
  ConsentChannel,
  DiagnosticResultInput,
  PaymentItem,
  PaymentMethod,
  QualityCheck,
  Quote,
  QuoteItemInput,
  QuoteOverview,
  RepairOverview,
  RepairTask,
} from "@/types/api";

const order = (id: string) => `/work-orders/${id}`;

// --- Quotations -----------------------------------------------------------------------

export async function getQuotes(orderId: string): Promise<QuoteOverview> {
  const { data } = await http.get<QuoteOverview>(`${order(orderId)}/quotes`);
  return data;
}

export async function createQuote(orderId: string): Promise<Quote> {
  const { data } = await http.post<Quote>(`${order(orderId)}/quotes`);
  return data;
}

export async function saveQuote(
  orderId: string,
  quoteId: string,
  items: QuoteItemInput[],
  notes: string | null,
): Promise<Quote> {
  const { data } = await http.put<Quote>(`${order(orderId)}/quotes/${quoteId}`, { items, notes });
  return data;
}

export async function discardQuote(orderId: string, quoteId: string): Promise<void> {
  await http.delete(`${order(orderId)}/quotes/${quoteId}`);
}

export async function sendQuote(orderId: string, quoteId: string): Promise<Quote> {
  const { data } = await http.post<Quote>(`${order(orderId)}/quotes/${quoteId}/send`);
  return data;
}

export async function respondQuote(
  orderId: string,
  quoteId: string,
  accepted: boolean,
  channel: ConsentChannel,
  reason: string | null,
): Promise<Quote> {
  const { data } = await http.post<Quote>(`${order(orderId)}/quotes/${quoteId}/response`, {
    accepted,
    channel,
    reason,
  });
  return data;
}

export async function downloadQuote(orderId: string, quoteId: string): Promise<Blob> {
  const { data } = await http.get<Blob>(`${order(orderId)}/quotes/${quoteId}/pdf`, {
    responseType: "blob",
  });
  return data;
}

// --- Repair and quality control -------------------------------------------------------

export async function getRepair(orderId: string): Promise<RepairOverview> {
  const { data } = await http.get<RepairOverview>(`${order(orderId)}/repair`);
  return data;
}

export async function addTask(
  orderId: string,
  description: string,
  labor_minutes: number | null,
): Promise<RepairTask> {
  const { data } = await http.post<RepairTask>(`${order(orderId)}/repair/tasks`, {
    description,
    labor_minutes,
  });
  return data;
}

export async function consumePart(
  orderId: string,
  taskId: string,
  part_id: string,
  quantity: number,
): Promise<RepairTask> {
  const { data } = await http.post<RepairTask>(`${order(orderId)}/repair/tasks/${taskId}/parts`, {
    part_id,
    quantity,
  });
  return data;
}

export async function returnPart(
  orderId: string,
  taskId: string,
  repairPartId: string,
): Promise<RepairTask> {
  const { data } = await http.post<RepairTask>(
    `${order(orderId)}/repair/tasks/${taskId}/parts/${repairPartId}/return`,
  );
  return data;
}

export async function addQualityCheck(
  orderId: string,
  results: DiagnosticResultInput[],
  notes: string | null,
): Promise<QualityCheck> {
  const { data } = await http.post<QualityCheck>(`${order(orderId)}/repair/quality-checks`, {
    results,
    notes,
  });
  return data;
}

// --- Payments -------------------------------------------------------------------------

export async function getBilling(orderId: string): Promise<Billing> {
  const { data } = await http.get<Billing>(`${order(orderId)}/billing`);
  return data;
}

export async function registerPayment(
  orderId: string,
  amount: string,
  method: PaymentMethod,
  reference: string | null,
): Promise<PaymentItem> {
  const { data } = await http.post<PaymentItem>(`${order(orderId)}/payments`, {
    amount,
    method,
    reference,
  });
  return data;
}

export async function downloadReceipt(orderId: string, paymentId: string): Promise<Blob> {
  const { data } = await http.get<Blob>(`${order(orderId)}/payments/${paymentId}/receipt.pdf`, {
    responseType: "blob",
  });
  return data;
}
