import { AlertCircle } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { FormField } from "@/components/FormField";
import { Alert, AlertDescription } from "@/components/ui/alert";
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
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { errorMessage } from "@/services/errors";
import type { WorkOrder, WorkOrderStatus } from "@/types/api";

import { PERMS, useCan } from "@/modules/auth/permissions";
import { useBilling } from "@/modules/workshop/hooks";

import { useChangeStatus, useDeliver } from "../hooks";
import {
  formatMoney,
  NEGATIVE_TRANSITIONS,
  reasonRequired,
  STATUS_LABELS,
  TRANSITION_ACTIONS,
} from "../presentation";

/** Confirms a status change; asks for the reason when the transition needs one. */
export function StatusChangeDialog({
  order,
  target,
  onClose,
}: {
  order: WorkOrder;
  target: WorkOrderStatus;
  onClose: () => void;
}) {
  const change = useChangeStatus();
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const needsReason = reasonRequired(order.status, target);

  const submit = async () => {
    setError(null);
    try {
      await change.mutateAsync({ id: order.id, status: target, reason: reason.trim() || null });
      toast.success(`Orden en estado: ${STATUS_LABELS[target]}.`);
      onClose();
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{TRANSITION_ACTIONS[target]}</DialogTitle>
          <DialogDescription>
            {order.number}: {STATUS_LABELS[order.status]} → {STATUS_LABELS[target]}
          </DialogDescription>
        </DialogHeader>
        {error && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <div className="grid gap-1.5">
          <Label htmlFor="status-reason">
            {needsReason ? "Motivo (obligatorio)" : "Nota (opcional)"}
          </Label>
          <Textarea
            id="status-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={needsReason ? "Explique el motivo del cambio." : undefined}
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Volver
          </Button>
          <Button
            variant={NEGATIVE_TRANSITIONS.has(target) ? "destructive" : "default"}
            disabled={change.isPending || (needsReason && !reason.trim())}
            onClick={() => void submit()}
          >
            Confirmar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Delivery: by the customer, or by a third party with name and document. */
export function DeliveryDialog({ order, onClose }: { order: WorkOrder; onClose: () => void }) {
  const deliver = useDeliver();
  const billing = useBilling(order.id);
  const canWaive = useCan(PERMS.WORK_ORDERS_DELIVER_WITH_BALANCE);
  const [balanceReason, setBalanceReason] = useState("");
  const [warrantyDays, setWarrantyDays] = useState("");
  const [byCustomer, setByCustomer] = useState(true);
  const [name, setName] = useState("");
  const [document, setDocument] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const balance = Number(billing.data?.balance ?? 0);
  const owes = balance > 0;
  const valid =
    Boolean(billing.data) &&
    (byCustomer || (name.trim() && document.trim())) &&
    (!owes || (canWaive && balanceReason.trim()));

  const submit = async () => {
    setError(null);
    try {
      await deliver.mutateAsync({
        id: order.id,
        payload: {
          picked_up_by_customer: byCustomer,
          name: byCustomer ? null : name.trim(),
          document: byCustomer ? null : document.trim(),
          notes: notes.trim() || null,
          balance_reason: owes ? balanceReason.trim() : null,
          warranty_days: warrantyDays ? Number(warrantyDays) : null,
        },
      });
      toast.success("Equipo entregado.");
      onClose();
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Entregar equipo</DialogTitle>
          <DialogDescription>
            {order.number} · {order.device.manufacturer} {order.device.model}
          </DialogDescription>
        </DialogHeader>
        {error && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {owes && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>
              Saldo pendiente de {formatMoney(billing.data?.balance)}.{" "}
              {canWaive
                ? "Puede entregar indicando el motivo."
                : "Registre el pago antes de entregar o pida autorización a un supervisor."}
            </AlertDescription>
          </Alert>
        )}
        {owes && canWaive && (
          <div className="grid gap-1.5">
            <Label htmlFor="balance-reason">Motivo de la entrega con saldo</Label>
            <Textarea
              id="balance-reason"
              value={balanceReason}
              onChange={(e) => setBalanceReason(e.target.value)}
            />
          </div>
        )}
        <Label className="flex items-center gap-2 font-normal">
          <Checkbox checked={byCustomer} onCheckedChange={(v) => setByCustomer(v === true)} />
          Lo retira el cliente ({order.customer.full_name})
        </Label>
        {!byCustomer && (
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField
              label="Nombre de quien retira"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <FormField
              label="Documento"
              placeholder="CC 1234567"
              value={document}
              onChange={(e) => setDocument(e.target.value)}
            />
          </div>
        )}
        <FormField
          label="Días de garantía (opcional)"
          inputMode="numeric"
          placeholder="Por defecto, los del taller"
          hint="Solo aplica si el equipo se reparó."
          value={warrantyDays}
          onChange={(e) => setWarrantyDays(e.target.value.replace(/\D/g, "").slice(0, 4))}
        />
        <div className="grid gap-1.5">
          <Label htmlFor="delivery-notes">Observaciones (opcional)</Label>
          <Textarea id="delivery-notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Volver
          </Button>
          <Button disabled={!valid || deliver.isPending} onClick={() => void submit()}>
            Registrar entrega
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
