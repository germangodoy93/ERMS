import { CalendarClock, MapPin, MonitorSmartphone, User } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

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
import { Textarea } from "@/components/ui/textarea";
import { formatDateTime, formatPhone } from "@/lib/format";
import { formatMoney } from "@/modules/workorders/presentation";
import { errorMessage } from "@/services/errors";
import type { AppointmentRead } from "@/types/api";

import { useCancelAppointment } from "../hooks";
import {
  bogotaDate,
  CONSENT_CHANNEL_LABELS,
  durationLabel,
  formatDayTitle,
  MODALITY_LABELS,
  timeRange,
} from "../presentation";

interface AppointmentDetailDialogProps {
  appointment: AppointmentRead | null;
  canManage: boolean;
  onClose: () => void;
  onEdit: (appointment: AppointmentRead) => void;
}

export function AppointmentDetailDialog({
  appointment,
  canManage,
  onClose,
  onEdit,
}: AppointmentDetailDialogProps) {
  return (
    <Dialog open={appointment !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        {appointment && (
          <DetailBody
            key={appointment.id}
            appointment={appointment}
            canManage={canManage}
            onClose={onClose}
            onEdit={onEdit}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

function DetailBody({
  appointment: a,
  canManage,
  onClose,
  onEdit,
}: {
  appointment: AppointmentRead;
  canManage: boolean;
  onClose: () => void;
  onEdit: (appointment: AppointmentRead) => void;
}) {
  const [cancelling, setCancelling] = useState(false);
  const [reason, setReason] = useState("");
  const cancel = useCancelAppointment();
  const scheduled = a.status === "SCHEDULED";

  const confirmCancel = async () => {
    try {
      await cancel.mutateAsync({ id: a.id, reason });
      toast.success(`Cita ${a.number} cancelada.`);
      onClose();
    } catch (error) {
      toast.error(errorMessage(error, "No se pudo cancelar la cita."));
    }
  };

  return (
    <>
      <DialogHeader>
        <DialogTitle className="flex flex-wrap items-center gap-2">
          Cita {a.number}
          <Badge variant={a.modality === "REMOTE" ? "secondary" : "outline"}>
            {MODALITY_LABELS[a.modality]}
          </Badge>
          {!scheduled && <Badge variant="destructive">Cancelada</Badge>}
        </DialogTitle>
        <DialogDescription>{a.service.name}</DialogDescription>
      </DialogHeader>

      <dl className="grid gap-3 text-sm">
        <Row icon={<CalendarClock className="size-4" />} label="Cuándo">
          {formatDayTitle(bogotaDate(a.starts_at))}, {timeRange(a)} (
          {durationLabel(a.duration_minutes)})
        </Row>
        <Row icon={<User className="size-4" />} label="Cliente">
          {a.customer.full_name} · {formatPhone(a.customer.phone)}
        </Row>
        <Row icon={<User className="size-4" />} label="Técnico">
          {a.technician?.full_name ?? "Sin asignar"}
        </Row>
        {a.modality === "ON_SITE" ? (
          <Row icon={<MapPin className="size-4" />} label="Dirección">
            {a.address} · {a.locality}
          </Row>
        ) : (
          <Row icon={<MonitorSmartphone className="size-4" />} label="Acceso remoto">
            Autorizado (
            {a.remote_consent_channel && CONSENT_CHANNEL_LABELS[a.remote_consent_channel]}) el{" "}
            {formatDateTime(a.remote_consent_at)}. El código de la sesión no se guarda.
          </Row>
        )}
        <Row label="Precio">
          {a.service.price === null
            ? "Según el diagnóstico"
            : `${formatMoney(a.service.price)}${a.service.tax_rate ? (a.service.price_includes_tax ? " IVA incluido" : " + IVA") : ""}`}
        </Row>
        <Row label="Qué necesita">
          <span className="whitespace-pre-line">{a.reason}</span>
        </Row>
        {a.notes && (
          <Row label="Notas">
            <span className="whitespace-pre-line">{a.notes}</span>
          </Row>
        )}
        {a.overlap_reason && (
          <Row label="Cruce con otra cita">
            <span className="whitespace-pre-line">{a.overlap_reason}</span>
          </Row>
        )}
        {a.cancel_reason && (
          <Row label="Motivo de cancelación">
            {a.cancel_reason} ({formatDateTime(a.cancelled_at)})
          </Row>
        )}
        <Row label="Agendada">
          {formatDateTime(a.created_at)}
          {a.created_by ? ` por ${a.created_by.full_name}` : ""}
        </Row>
      </dl>

      {cancelling && (
        <div className="grid gap-1.5">
          <Label htmlFor="cancel-reason">Motivo de la cancelación</Label>
          <Textarea id="cancel-reason" value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
      )}

      <DialogFooter>
        {canManage && scheduled && !cancelling && (
          <>
            <Button variant="outline" onClick={() => setCancelling(true)}>
              Cancelar cita
            </Button>
            <Button onClick={() => onEdit(a)}>Mover o editar</Button>
          </>
        )}
        {cancelling && (
          <>
            <Button variant="outline" onClick={() => setCancelling(false)}>
              Volver
            </Button>
            <Button
              variant="destructive"
              disabled={reason.trim().length < 3 || cancel.isPending}
              onClick={() => void confirmCancel()}
            >
              Confirmar cancelación
            </Button>
          </>
        )}
      </DialogFooter>
    </>
  );
}

function Row({
  icon,
  label,
  children,
}: {
  icon?: React.ReactNode;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-[8rem_1fr] gap-2">
      <dt className="text-muted-foreground flex items-center gap-1.5">
        {icon}
        {label}
      </dt>
      <dd>{children}</dd>
    </div>
  );
}
