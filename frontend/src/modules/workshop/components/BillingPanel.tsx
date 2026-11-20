import { FileDown, Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { SelectField } from "@/components/SelectField";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { saveBlob } from "@/lib/download";
import { formatDateTime } from "@/lib/format";
import { formatMoney, PAYMENT_LABELS, parseMoney } from "@/modules/workorders/presentation";
import { errorMessage } from "@/services/errors";
import { PAYMENT_METHODS, type Billing, type PaymentMethod, type WorkOrder } from "@/types/api";

import { downloadReceipt } from "../api";
import { useBilling, useRegisterPayment } from "../hooks";
import { balanceLabel } from "../presentation";

export function BillingPanel({ order }: { order: WorkOrder }) {
  const billing = useBilling(order.id);
  if (billing.isPending) return <Skeleton className="h-24" />;
  if (billing.isError)
    return <p className="text-destructive text-sm">{errorMessage(billing.error)}</p>;
  const data = billing.data;
  return (
    <div className="grid gap-4">
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-muted-foreground">Valor del servicio</dt>
          <dd className="font-medium">{formatMoney(data.amount_due)}</dd>
          <dd className="text-muted-foreground text-xs">
            {data.accepted_quote_total
              ? "Cotización aprobada (incluye diagnóstico)"
              : "Diagnóstico"}
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Pagado</dt>
          <dd className="font-medium">{formatMoney(data.paid)}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">{balanceLabel(data.balance)}</dt>
          <dd className="text-lg font-semibold">
            {formatMoney(String(Math.abs(Number(data.balance))))}
          </dd>
        </div>
      </dl>
      {data.payments.length > 0 && (
        <ul className="divide-y rounded-md border text-sm">
          {data.payments.map((p) => (
            <li key={p.id} className="flex flex-wrap items-center gap-2 p-2">
              <span className="font-mono text-xs">{p.receipt_number ?? "Anticipo"}</span>
              <span>{formatMoney(p.amount)}</span>
              <span className="text-muted-foreground">
                {PAYMENT_LABELS[p.method]}
                {p.reference ? ` · ${p.reference}` : ""} · {formatDateTime(p.paid_at)}
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="ml-auto"
                onClick={() =>
                  void downloadReceipt(order.id, p.id)
                    .then((blob) => saveBlob(blob, `${p.receipt_number ?? "anticipo"}.pdf`))
                    .catch((e: unknown) => toast.error(errorMessage(e)))
                }
              >
                <FileDown /> Comprobante
              </Button>
            </li>
          ))}
        </ul>
      )}
      {data.can_register && <PaymentForm orderId={order.id} billing={data} />}
      <p className="text-muted-foreground text-xs">
        Los comprobantes son internos y no reemplazan la factura electrónica.
      </p>
    </div>
  );
}

function PaymentForm({ orderId, billing }: { orderId: string; billing: Billing }) {
  const register = useRegisterPayment(orderId);
  const [amount, setAmount] = useState(String(Number(billing.balance)));
  const [method, setMethod] = useState<PaymentMethod>("CASH");
  const [reference, setReference] = useState("");
  const parsed = parseMoney(amount);

  const submit = async () => {
    if (!parsed) return;
    try {
      const payment = await register.mutateAsync({
        amount: parsed,
        method,
        reference: reference.trim() || null,
      });
      toast.success(`Pago registrado: ${payment.receipt_number}.`);
      setReference("");
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };

  return (
    <div className="flex flex-wrap items-end gap-2 rounded-md border border-dashed p-3">
      <div className="grid gap-1.5">
        <span className="text-sm font-medium">Valor</span>
        <Input
          className="w-36"
          aria-label="Valor del pago"
          inputMode="numeric"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
      </div>
      <div className="w-44">
        <SelectField
          label="Medio"
          value={method}
          onChange={(v) => setMethod(v as PaymentMethod)}
          options={PAYMENT_METHODS.map((m) => ({ value: m, label: PAYMENT_LABELS[m] }))}
        />
      </div>
      <div className="grid gap-1.5">
        <span className="text-sm font-medium">Referencia</span>
        <Input
          className="w-40"
          aria-label="Referencia del pago"
          placeholder="Opcional"
          value={reference}
          onChange={(e) => setReference(e.target.value)}
        />
      </div>
      <Button
        className="ml-auto"
        disabled={!parsed || Number(parsed) <= 0 || register.isPending}
        onClick={() => void submit()}
      >
        <Plus /> Registrar pago
      </Button>
    </div>
  );
}
