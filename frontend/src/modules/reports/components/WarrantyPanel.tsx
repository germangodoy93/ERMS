import { AlertCircle, ShieldCheck, ShieldOff } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { toast } from "sonner";

import { SelectField } from "@/components/SelectField";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { formatDateTime } from "@/lib/format";
import { UNLOCK_LABELS } from "@/modules/workorders/presentation";
import { errorMessage } from "@/services/errors";
import { UNLOCK_METHODS, type UnlockMethod, type WarrantyClaim, type WorkOrder } from "@/types/api";

import { useDecideClaim, useOpenClaim, useWarranty } from "../hooks";

const CLAIM_STATUS: Record<WarrantyClaim["status"], string> = {
  OPEN: "Abierto",
  ACCEPTED: "Aceptado",
  REJECTED: "Rechazado",
};

export function WarrantyPanel({ order }: { order: WorkOrder }) {
  const overview = useWarranty(order.id);
  const [claiming, setClaiming] = useState(false);
  const [deciding, setDeciding] = useState<WarrantyClaim | null>(null);
  if (overview.isPending) return <Skeleton className="h-16" />;
  if (overview.isError)
    return <p className="text-destructive text-sm">{errorMessage(overview.error)}</p>;
  const { warranty, claims, is_claim_order, can_claim, can_decide } = overview.data;

  return (
    <div className="grid gap-3 text-sm">
      {is_claim_order && warranty && (
        <p>
          Esta orden atiende un reclamo de garantía de{" "}
          <Link to={`/ordenes/${warranty.work_order_id}`} className="font-mono underline">
            {warranty.work_order_number}
          </Link>
          .
        </p>
      )}
      {!warranty ? (
        <p className="text-muted-foreground">
          {order.status === "ENTREGADO"
            ? "Esta orden no tiene garantía (no se reparó)."
            : "La garantía se crea al entregar un equipo reparado."}
        </p>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          {warranty.active ? (
            <ShieldCheck className="text-success size-4" />
          ) : (
            <ShieldOff className="text-muted-foreground size-4" />
          )}
          <span>
            {warranty.days} días: del {warranty.starts_on} al {warranty.ends_on}
          </span>
          <Badge variant="outline">{warranty.active ? "Vigente" : "Vencida"}</Badge>
          {can_claim && (
            <Button size="sm" className="ml-auto" onClick={() => setClaiming(true)}>
              Abrir reclamo de garantía
            </Button>
          )}
        </div>
      )}
      {claims.length > 0 && (
        <ul className="divide-y rounded-md border">
          {claims.map((c) => (
            <li key={c.id} className="grid gap-1 p-2">
              <div className="flex flex-wrap items-center gap-2">
                <Link to={`/ordenes/${c.claim_order_id}`} className="font-mono underline">
                  {c.claim_order_number}
                </Link>
                <Badge variant="outline">{CLAIM_STATUS[c.status]}</Badge>
                <span className="text-muted-foreground text-xs">
                  {formatDateTime(c.created_at)}
                </span>
                {can_decide && c.status === "OPEN" && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="ml-auto"
                    onClick={() => setDeciding(c)}
                  >
                    Resolver
                  </Button>
                )}
              </div>
              <p>{c.reported_issue}</p>
              {c.resolution && (
                <p className="text-muted-foreground">
                  Resolución: {c.resolution} ({c.decided_by?.full_name ?? "—"})
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
      {claiming && <ClaimDialog order={order} onClose={() => setClaiming(false)} />}
      {deciding && (
        <DecideDialog orderId={order.id} claim={deciding} onClose={() => setDeciding(null)} />
      )}
    </div>
  );
}

function ClaimDialog({ order, onClose }: { order: WorkOrder; onClose: () => void }) {
  const open = useOpenClaim(order.id);
  const navigate = useNavigate();
  const [issue, setIssue] = useState("");
  const [condition, setCondition] = useState("");
  const [unlock, setUnlock] = useState<UnlockMethod>("NOT_REQUIRED");
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setError(null);
    try {
      const created = await open.mutateAsync({
        reported_issue: issue.trim(),
        physical_condition: condition.trim(),
        unlock_method: unlock,
      });
      toast.success(`Reclamo abierto: orden ${created.number}.`);
      onClose();
      void navigate(`/ordenes/${created.id}`);
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <Dialog open onOpenChange={(value) => !value && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Reclamo de garantía</DialogTitle>
          <DialogDescription>
            Se abre una orden nueva para el mismo equipo, sin cobro de diagnóstico.
          </DialogDescription>
        </DialogHeader>
        {error && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <div className="grid gap-1.5">
          <Label htmlFor="claim-issue">Falla que reporta el cliente</Label>
          <Textarea id="claim-issue" value={issue} onChange={(e) => setIssue(e.target.value)} />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="claim-condition">Estado físico al recibirlo</Label>
          <Textarea
            id="claim-condition"
            value={condition}
            onChange={(e) => setCondition(e.target.value)}
          />
        </div>
        <SelectField
          label="Desbloqueo"
          value={unlock}
          onChange={(v) => setUnlock(v as UnlockMethod)}
          options={UNLOCK_METHODS.map((m) => ({ value: m, label: UNLOCK_LABELS[m] }))}
        />
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            disabled={issue.trim().length < 5 || condition.trim().length < 3 || open.isPending}
            onClick={() => void submit()}
          >
            Abrir reclamo
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DecideDialog({
  orderId,
  claim,
  onClose,
}: {
  orderId: string;
  claim: WarrantyClaim;
  onClose: () => void;
}) {
  const decide = useDecideClaim(orderId);
  const [resolution, setResolution] = useState("");
  const submit = async (accepted: boolean) => {
    try {
      await decide.mutateAsync({ claimId: claim.id, accepted, resolution: resolution.trim() });
      toast.success(accepted ? "Reclamo aceptado." : "Reclamo rechazado.");
      onClose();
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };
  const ready = resolution.trim().length >= 5 && !decide.isPending;
  return (
    <Dialog open onOpenChange={(value) => !value && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Resolver reclamo {claim.claim_order_number}</DialogTitle>
          <DialogDescription>{claim.reported_issue}</DialogDescription>
        </DialogHeader>
        <div className="grid gap-1.5">
          <Label htmlFor="claim-resolution">Resolución</Label>
          <Textarea
            id="claim-resolution"
            placeholder="Ej.: defecto del repuesto, se cambia sin costo / golpe posterior, no cubre"
            value={resolution}
            onChange={(e) => setResolution(e.target.value)}
          />
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            className="text-destructive"
            disabled={!ready}
            onClick={() => void submit(false)}
          >
            Rechazar
          </Button>
          <Button disabled={!ready} onClick={() => void submit(true)}>
            Aceptar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
