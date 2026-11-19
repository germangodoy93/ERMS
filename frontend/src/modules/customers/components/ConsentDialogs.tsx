import { AlertCircle, AlertTriangle } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { SelectField } from "@/components/SelectField";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
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
import { useCurrentPolicy } from "@/modules/organization/hooks";
import { errorMessage } from "@/services/errors";
import {
  CONSENT_CHANNELS,
  type ConsentChannel,
  type ConsentPurpose,
  type Customer,
} from "@/types/api";

import { useAnonymizeCustomer, useChangeConsent } from "../hooks";
import { CHANNEL_LABELS, PURPOSE_LABELS } from "../presentation";

const CHANNEL_OPTIONS = CONSENT_CHANNELS.map((c) => ({ value: c, label: CHANNEL_LABELS[c] }));

export interface ConsentAction {
  purpose: ConsentPurpose;
  granted: boolean;
}

/** Grant or revoke one authorization, recording how the customer expressed it. */
export function ConsentChangeDialog({
  customer,
  action,
  onClose,
}: {
  customer: Customer;
  action: ConsentAction | null;
  onClose: () => void;
}) {
  const policy = useCurrentPolicy();
  const change = useChangeConsent();
  const [channel, setChannel] = useState<ConsentChannel>("SCREEN");
  const [error, setError] = useState<string | null>(null);

  if (!action) return null;
  const label = PURPOSE_LABELS[action.purpose];

  const submit = async () => {
    setError(null);
    try {
      await change.mutateAsync({ id: customer.id, change: { ...action, channel } });
      toast.success(action.granted ? "Autorización registrada." : "Autorización revocada.");
      onClose();
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {action.granted ? "Otorgar" : "Revocar"}: {label}
          </DialogTitle>
          <DialogDescription>{customer.full_name}</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4">
          {error && (
            <Alert variant="destructive">
              <AlertCircle />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {action.granted ? (
            <p className="bg-muted rounded-md p-3 text-sm leading-relaxed">
              {policy.data?.authorizations[action.purpose] ?? "…"}
            </p>
          ) : (
            <Alert>
              <AlertTriangle />
              <AlertDescription>
                {action.purpose === "DATA_PROCESSING"
                  ? "Sin esta autorización no se pueden registrar equipos ni recibir órdenes de este cliente."
                  : "La revocación queda registrada; el historial no se borra."}
              </AlertDescription>
            </Alert>
          )}
          <SelectField
            label="Medio"
            value={channel}
            onChange={(v) => setChannel(v as ConsentChannel)}
            options={CHANNEL_OPTIONS}
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            variant={action.granted ? "default" : "destructive"}
            onClick={() => void submit()}
            disabled={change.isPending}
          >
            {action.granted ? "Registrar autorización" : "Revocar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Irreversible: requires typing the customer's name to confirm. */
export function AnonymizeDialog({
  customer,
  open,
  onClose,
}: {
  customer: Customer;
  open: boolean;
  onClose: () => void;
}) {
  const anonymize = useAnonymizeCustomer();
  const [channel, setChannel] = useState<ConsentChannel>("PAPER");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const confirmed = confirmation.trim() === customer.full_name;

  const submit = async () => {
    setError(null);
    try {
      await anonymize.mutateAsync({ id: customer.id, channel });
      toast.success("Cliente anonimizado.");
      onClose();
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <Dialog open={open} onOpenChange={(value) => !value && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Anonimizar cliente</DialogTitle>
          <DialogDescription>Derecho de supresión (Ley 1581 de 2012).</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4">
          <Alert variant="destructive">
            <AlertTriangle />
            <AlertTitle>Esta acción no se puede deshacer</AlertTitle>
            <AlertDescription>
              Se borran el nombre, documento, teléfono, correo, dirección y notas del cliente y las
              notas de sus equipos, y se revocan sus autorizaciones. Se conserva el historial
              técnico de los equipos sin datos personales.
            </AlertDescription>
          </Alert>
          {error && (
            <Alert variant="destructive">
              <AlertCircle />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <SelectField
            label="¿Cómo lo solicitó el titular?"
            value={channel}
            onChange={(v) => setChannel(v as ConsentChannel)}
            options={CHANNEL_OPTIONS}
          />
          <div className="grid gap-1.5">
            <Label htmlFor="anonymize-confirm">
              Escriba <span className="font-semibold">{customer.full_name}</span> para confirmar
            </Label>
            <Input
              id="anonymize-confirm"
              autoComplete="off"
              value={confirmation}
              onChange={(e) => setConfirmation(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            variant="destructive"
            disabled={!confirmed || anonymize.isPending}
            onClick={() => void submit()}
          >
            Anonimizar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
