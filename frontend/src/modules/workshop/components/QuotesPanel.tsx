import { AlertCircle, Check, FileDown, Plus, Send, Trash2, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { SelectField } from "@/components/SelectField";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { saveBlob } from "@/lib/download";
import { formatDateTime } from "@/lib/format";
import { CHANNEL_LABELS } from "@/modules/customers/presentation";
import { useParts } from "@/modules/inventory/hooks";
import { formatMoney } from "@/modules/workorders/presentation";
import { errorMessage } from "@/services/errors";
import {
  CONSENT_CHANNELS,
  type ConsentChannel,
  type Quote,
  type QuoteOverview,
  type WorkOrder,
} from "@/types/api";

import { downloadQuote } from "../api";
import { useQuoteActions, useQuotes } from "../hooks";
import { QUOTE_STATUS_LABELS, QUOTE_STATUS_TONE } from "../presentation";
import { toLines, toPayload, type DraftLine } from "../quotePayload";

export function QuotesPanel({ order }: { order: WorkOrder }) {
  const overview = useQuotes(order.id);
  if (overview.isPending) return <Skeleton className="h-40" />;
  if (overview.isError) {
    return <p className="text-destructive text-sm">{errorMessage(overview.error)}</p>;
  }
  const data = overview.data;
  const [current, ...previous] = data.quotes;
  return (
    <div className="grid gap-4">
      {!current && <NoQuote order={order} data={data} />}
      {current?.status === "DRAFT" ? (
        <DraftEditor key={current.id + current.total} order={order} data={data} quote={current} />
      ) : (
        current && <QuoteView order={order} data={data} quote={current} />
      )}
      {current && current.status !== "DRAFT" && data.can_edit && current.status !== "ACCEPTED" && (
        <NewVersionButton orderId={order.id} />
      )}
      {previous.length > 0 && (
        <details className="text-sm">
          <summary className="text-muted-foreground cursor-pointer">
            Versiones anteriores ({previous.length})
          </summary>
          <ul className="mt-2 grid gap-1">
            {previous.map((q) => (
              <li key={q.id} className="flex flex-wrap items-center gap-2">
                <span>Versión {q.version}</span>
                <StatusBadge status={q.status} />
                <span className="text-muted-foreground">{formatMoney(q.total)}</span>
                <PdfButton orderId={order.id} quote={q} number={order.number} />
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: Quote["status"] }) {
  return (
    <Badge variant="outline" className={QUOTE_STATUS_TONE[status]}>
      {QUOTE_STATUS_LABELS[status]}
    </Badge>
  );
}

function PdfButton({ orderId, quote, number }: { orderId: string; quote: Quote; number: string }) {
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() =>
        void downloadQuote(orderId, quote.id)
          .then((blob) => saveBlob(blob, `cotizacion-${number}-v${quote.version}.pdf`))
          .catch((e: unknown) => toast.error(errorMessage(e)))
      }
    >
      <FileDown /> PDF
    </Button>
  );
}

function NoQuote({ order, data }: { order: WorkOrder; data: QuoteOverview }) {
  const actions = useQuoteActions(order.id);
  if (!data.can_edit) {
    return (
      <p className="text-muted-foreground text-sm">
        La cotización se elabora cuando la orden está en Cotización.
      </p>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-3">
      <p className="text-muted-foreground text-sm">
        Diagnóstico: {formatMoney(data.diagnostic_fee)} (se incluye si el cliente aprueba).
      </p>
      <Button
        onClick={() =>
          void actions.create.mutateAsync().catch((e: unknown) => toast.error(errorMessage(e)))
        }
      >
        <Plus /> Crear cotización
      </Button>
    </div>
  );
}

function NewVersionButton({ orderId }: { orderId: string }) {
  const actions = useQuoteActions(orderId);
  return (
    <Button
      variant="outline"
      className="w-fit"
      onClick={() =>
        void actions.create
          .mutateAsync()
          .then(() => toast.success("Nueva versión en borrador."))
          .catch((e: unknown) => toast.error(errorMessage(e)))
      }
    >
      <Plus /> Nueva versión (cambios del cliente)
    </Button>
  );
}

function Totals({ quote }: { quote: Quote }) {
  return (
    <dl className="ml-auto grid w-full max-w-xs grid-cols-2 gap-1 text-sm">
      <dt className="text-muted-foreground">Descuentos aplicados</dt>
      <dd className="text-right">{formatMoney(quote.discount_total)}</dd>
      <dt className="text-muted-foreground">Subtotal sin IVA</dt>
      <dd className="text-right">{formatMoney(quote.subtotal)}</dd>
      <dt className="text-muted-foreground">IVA</dt>
      <dd className="text-right">{formatMoney(quote.tax_total)}</dd>
      <dt className="font-semibold">Total</dt>
      <dd className="text-right font-semibold">{formatMoney(quote.total)}</dd>
    </dl>
  );
}

function DraftEditor({
  order,
  data,
  quote,
}: {
  order: WorkOrder;
  data: QuoteOverview;
  quote: Quote;
}) {
  const actions = useQuoteActions(order.id);
  const parts = useParts({});
  const [lines, setLines] = useState<DraftLine[]>(() => toLines(quote));
  const [notes, setNotes] = useState(quote.notes ?? "");
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const update = (index: number, patch: Partial<DraftLine>) => {
    setLines((current) => current.map((l, i) => (i === index ? { ...l, ...patch } : l)));
    setDirty(true);
  };
  const add = (kind: DraftLine["kind"]) => {
    setLines((current) => [
      ...current,
      {
        kind,
        part_id: "",
        description: "",
        quantity: "1",
        unit_price: "",
        discount_percent: "0",
        apply_tax: false,
        price_includes_tax: false,
      },
    ]);
    setDirty(true);
  };
  const choosePart = (index: number, partId: string) => {
    const part = parts.data?.find((p) => p.id === partId);
    update(index, {
      part_id: partId,
      description: part?.name ?? "",
      unit_price: part ? String(Number(part.sale_price)) : "",
      apply_tax: (part?.tax_rate ?? 0) > 0,
      price_includes_tax: part?.price_includes_tax ?? false,
    });
  };

  const save = async () => {
    setError(null);
    const payload = toPayload(lines);
    if (typeof payload === "string") return setError(payload);
    try {
      await actions.save.mutateAsync({
        quoteId: quote.id,
        items: payload,
        notes: notes.trim() || null,
      });
      setDirty(false);
      toast.success("Cotización guardada.");
    } catch (e) {
      setError(errorMessage(e));
    }
  };
  const send = async () => {
    try {
      await actions.send.mutateAsync(quote.id);
      toast.success("Cotización enviada. La orden queda pendiente de autorización del cliente.");
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium">Versión {quote.version}</span>
        <StatusBadge status={quote.status} />
        <span className="text-muted-foreground text-xs">
          Descuento máximo por ítem: {data.max_discount_percent} %
        </span>
      </div>
      {error && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <div className="grid gap-3">
        {lines.map((line, index) => (
          <div key={index} className="grid gap-2 rounded-md border p-3 text-sm">
            <div className="flex flex-wrap items-end gap-2">
              <Badge variant="outline">{line.kind === "LABOR" ? "Mano de obra" : "Repuesto"}</Badge>
              {line.kind === "PART" && (
                <div className="min-w-56 flex-1">
                  <SelectField
                    label="Del inventario (opcional)"
                    value={line.part_id}
                    emptyLabel="Repuesto por pedir"
                    onChange={(v) => (v ? choosePart(index, v) : update(index, { part_id: "" }))}
                    options={(parts.data ?? []).map((p) => ({
                      value: p.id,
                      label: `${p.sku} · ${p.name} (stock ${p.stock})`,
                    }))}
                  />
                </div>
              )}
              <Button
                variant="ghost"
                size="icon"
                className="ml-auto"
                aria-label={`Quitar ítem ${index + 1}`}
                onClick={() => {
                  setLines((current) => current.filter((_, i) => i !== index));
                  setDirty(true);
                }}
              >
                <Trash2 />
              </Button>
            </div>
            <Input
              aria-label={`Descripción del ítem ${index + 1}`}
              placeholder="Descripción"
              value={line.description}
              onChange={(e) => update(index, { description: e.target.value })}
            />
            <div className="grid grid-cols-3 gap-2">
              <Input
                aria-label={`Cantidad del ítem ${index + 1}`}
                inputMode="decimal"
                value={line.quantity}
                onChange={(e) => update(index, { quantity: e.target.value })}
              />
              <Input
                aria-label={`Valor unitario del ítem ${index + 1}`}
                inputMode="numeric"
                placeholder="Valor unitario"
                value={line.unit_price}
                onChange={(e) => update(index, { unit_price: e.target.value })}
              />
              <Input
                aria-label={`Descuento % del ítem ${index + 1}`}
                inputMode="decimal"
                placeholder="Desc. %"
                value={line.discount_percent}
                onChange={(e) => update(index, { discount_percent: e.target.value })}
              />
            </div>
            <div className="flex flex-wrap gap-4">
              <Label className="flex items-center gap-2 font-normal">
                <Checkbox
                  checked={line.apply_tax}
                  onCheckedChange={(v) => update(index, { apply_tax: v === true })}
                />
                Aplicar IVA 19 %
              </Label>
              {line.apply_tax && (
                <Label className="flex items-center gap-2 font-normal">
                  <Checkbox
                    checked={line.price_includes_tax}
                    onCheckedChange={(v) => update(index, { price_includes_tax: v === true })}
                  />
                  El valor ya incluye IVA
                </Label>
              )}
              {!dirty && quote.items[index] && (
                <span className="text-muted-foreground ml-auto">
                  Total ítem: {formatMoney(quote.items[index].total_amount)}
                </span>
              )}
            </div>
          </div>
        ))}
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => add("LABOR")}>
            <Plus /> Mano de obra
          </Button>
          <Button variant="outline" size="sm" onClick={() => add("PART")}>
            <Plus /> Repuesto
          </Button>
        </div>
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor="quote-notes">Observaciones para el cliente (opcional)</Label>
        <Textarea
          id="quote-notes"
          value={notes}
          onChange={(e) => {
            setNotes(e.target.value);
            setDirty(true);
          }}
        />
      </div>
      {dirty ? (
        <p className="text-muted-foreground text-right text-sm">
          Guarde para recalcular los totales.
        </p>
      ) : (
        <Totals quote={quote} />
      )}
      <div className="flex flex-wrap justify-end gap-2">
        <Button
          variant="ghost"
          onClick={() =>
            void actions.discard
              .mutateAsync(quote.id)
              .catch((e: unknown) => setError(errorMessage(e)))
          }
        >
          Descartar borrador
        </Button>
        <PdfButton orderId={order.id} quote={quote} number={order.number} />
        <Button
          variant="outline"
          disabled={!dirty || actions.save.isPending}
          onClick={() => void save()}
        >
          Guardar
        </Button>
        {data.can_send && (
          <Button
            disabled={dirty || quote.items.length === 0 || actions.send.isPending}
            onClick={() => void send()}
          >
            <Send /> Enviar al cliente
          </Button>
        )}
      </div>
    </div>
  );
}

function QuoteView({
  order,
  data,
  quote,
}: {
  order: WorkOrder;
  data: QuoteOverview;
  quote: Quote;
}) {
  const [responding, setResponding] = useState<boolean | null>(null);
  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium">Versión {quote.version}</span>
        <StatusBadge status={quote.status} />
        {quote.valid_until && (
          <span className="text-muted-foreground text-xs">Válida hasta {quote.valid_until}</span>
        )}
        {quote.responded_at && (
          <span className="text-muted-foreground text-xs">
            Respuesta: {formatDateTime(quote.responded_at)}
            {quote.response_channel ? ` · ${CHANNEL_LABELS[quote.response_channel]}` : ""}
          </span>
        )}
        <div className="ml-auto">
          <PdfButton orderId={order.id} quote={quote} number={order.number} />
        </div>
      </div>
      <ul className="divide-y rounded-md border text-sm">
        {quote.items.map((item) => (
          <li key={item.id} className="flex flex-wrap items-center gap-2 p-2">
            <span className="flex-1">
              {item.description}
              {item.sku && <span className="text-muted-foreground"> · {item.sku}</span>}
            </span>
            <span className="text-muted-foreground">
              {Number(item.quantity)} × {formatMoney(item.unit_price)}
              {Number(item.discount_percent) > 0 ? ` − ${Number(item.discount_percent)} %` : ""}
              {item.tax_rate ? ` · IVA ${item.tax_rate} %` : ""}
            </span>
            <span className="w-28 text-right">{formatMoney(item.total_amount)}</span>
          </li>
        ))}
      </ul>
      <Totals quote={quote} />
      {quote.discount_authorized_by && (
        <p className="text-muted-foreground text-xs">
          Descuento autorizado por {quote.discount_authorized_by.full_name}.
        </p>
      )}
      {data.can_respond && quote.status === "SENT" && (
        <div className="flex justify-end gap-2">
          <Button
            variant="outline"
            className="text-destructive"
            onClick={() => setResponding(false)}
          >
            <X /> Cliente rechazó
          </Button>
          <Button onClick={() => setResponding(true)}>
            <Check /> Cliente aprobó
          </Button>
        </div>
      )}
      {quote.status === "EXPIRED" && (
        <p className="text-muted-foreground text-sm">
          La cotización venció. Cree una nueva versión para enviarla de nuevo.
        </p>
      )}
      {responding !== null && (
        <RespondDialog
          orderId={order.id}
          quote={quote}
          accepted={responding}
          onClose={() => setResponding(null)}
        />
      )}
    </div>
  );
}

function RespondDialog({
  orderId,
  quote,
  accepted,
  onClose,
}: {
  orderId: string;
  quote: Quote;
  accepted: boolean;
  onClose: () => void;
}) {
  const actions = useQuoteActions(orderId);
  const [channel, setChannel] = useState<ConsentChannel>("VERBAL");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const submit = async () => {
    setError(null);
    try {
      await actions.respond.mutateAsync({
        quoteId: quote.id,
        accepted,
        channel,
        reason: reason.trim() || null,
      });
      toast.success(accepted ? "Reparación aprobada." : "Cotización rechazada.");
      onClose();
    } catch (e) {
      setError(errorMessage(e));
    }
  };
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{accepted ? "El cliente aprobó" : "El cliente rechazó"}</DialogTitle>
          <DialogDescription>
            Versión {quote.version} · {formatMoney(quote.total)}
          </DialogDescription>
        </DialogHeader>
        {error && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <SelectField
          label="¿Cómo respondió?"
          value={channel}
          onChange={(v) => setChannel(v as ConsentChannel)}
          options={CONSENT_CHANNELS.map((c) => ({ value: c, label: CHANNEL_LABELS[c] }))}
        />
        {!accepted && (
          <div className="grid gap-1.5">
            <Label htmlFor="reject-reason">Motivo del rechazo</Label>
            <Textarea
              id="reject-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Volver
          </Button>
          <Button
            variant={accepted ? "default" : "destructive"}
            disabled={actions.respond.isPending || (!accepted && !reason.trim())}
            onClick={() => void submit()}
          >
            Confirmar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
