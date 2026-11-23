import { AlertCircle, ArrowLeft, FileDown, PackageCheck } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router";
import { toast } from "sonner";

import { SelectField } from "@/components/SelectField";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { saveBlob } from "@/lib/download";
import { formatDateTime, formatPhone } from "@/lib/format";
import { PERMS, useCan } from "@/modules/auth/permissions";
import { AssemblyChecklistPanel } from "@/modules/assembly/components/AssemblyChecklistPanel";
import { DiagnosticPanel } from "@/modules/diagnostics/components/DiagnosticPanel";
import { WarrantyPanel } from "@/modules/reports/components/WarrantyPanel";
import { BillingPanel } from "@/modules/workshop/components/BillingPanel";
import { QuotesPanel } from "@/modules/workshop/components/QuotesPanel";
import { RepairPanel } from "@/modules/workshop/components/RepairPanel";
import { ImeiCheckButton } from "@/modules/devices/components/ImeiCheckButton";
import { errorMessage } from "@/services/errors";
import type { WorkOrder, WorkOrderStatus } from "@/types/api";

import { downloadReceptionAct } from "../api";
import { DeliveryDialog, StatusChangeDialog } from "../components/OrderActionDialogs";
import { PhotoGallery } from "../components/PhotoGallery";
import { WorkOrderStatusBadge } from "../components/WorkOrderStatusBadge";
import { useAssign, useTechnicians, useWorkOrder } from "../hooks";
import {
  accessoriesText,
  formatMoney,
  NEGATIVE_TRANSITIONS,
  QUOTE_DRIVEN,
  PAYMENT_LABELS,
  PRIORITY_LABELS,
  STATUS_LABELS,
  TRANSITION_ACTIONS,
  UNLOCK_LABELS,
} from "../presentation";

export function WorkOrderDetailPage() {
  const { orderId = "" } = useParams();
  const order = useWorkOrder(orderId);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <Link
        to="/ordenes"
        className="text-muted-foreground hover:text-foreground flex w-fit items-center gap-1 text-sm"
      >
        <ArrowLeft className="size-4" /> Órdenes de servicio
      </Link>
      {order.isPending && <Skeleton className="h-96" />}
      {order.isError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{errorMessage(order.error)}</AlertDescription>
        </Alert>
      )}
      {order.data && <OrderDetail order={order.data} />}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="contents">
      <dt className="text-muted-foreground text-sm">{label}</dt>
      <dd className="text-sm whitespace-pre-wrap">{children}</dd>
    </div>
  );
}

function OrderDetail({ order }: { order: WorkOrder }) {
  const [target, setTarget] = useState<WorkOrderStatus | null>(null);
  const [delivering, setDelivering] = useState(false);
  const [downloading, setDownloading] = useState(false);
  // Delivery has its own dialog; quote-driven states are changed from the quotation.
  const transitions = order.allowed_transitions.filter(
    (s) => s !== "ENTREGADO" && !QUOTE_DRIVEN.has(s),
  );
  const canDeliver = order.allowed_transitions.includes("ENTREGADO");

  const download = async () => {
    setDownloading(true);
    try {
      saveBlob(await downloadReceptionAct(order.id), `acta-${order.number}.pdf`);
    } catch (error) {
      toast.error(errorMessage(error, "No se pudo descargar el acta."));
    } finally {
      setDownloading(false);
    }
  };

  return (
    <>
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="font-mono text-2xl font-semibold tracking-tight">{order.number}</h1>
            <WorkOrderStatusBadge status={order.status} />
          </div>
          <p className="text-muted-foreground text-sm">
            {order.device.manufacturer} {order.device.model} · Recibido el{" "}
            {formatDateTime(order.received_at)} · {order.branch}
          </p>
        </div>
        <Button variant="outline" onClick={() => void download()} disabled={downloading}>
          <FileDown /> Acta de recepción
        </Button>
      </header>

      {(transitions.length > 0 || canDeliver) && (
        <div className="flex flex-wrap gap-2">
          {transitions.map((status) => (
            <Button
              key={status}
              variant={NEGATIVE_TRANSITIONS.has(status) ? "outline" : "default"}
              className={NEGATIVE_TRANSITIONS.has(status) ? "text-destructive" : undefined}
              onClick={() => setTarget(status)}
            >
              {TRANSITION_ACTIONS[status]}
            </Button>
          ))}
          {canDeliver && (
            <Button onClick={() => setDelivering(true)}>
              <PackageCheck /> Entregar equipo
            </Button>
          )}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Cliente y equipo</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-[9rem_1fr] gap-x-4 gap-y-2">
              <Field label="Cliente">
                <Link to={`/clientes/${order.customer.id}`} className="hover:underline">
                  {order.customer.full_name}
                </Link>
              </Field>
              <Field label="Teléfono">{formatPhone(order.customer.phone)}</Field>
              <Field label="Equipo">
                {order.device.category} · {order.device.manufacturer} {order.device.model}
              </Field>
              <Field label="IMEI">
                {order.device.imei ? (
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="font-mono">{order.device.imei}</span>
                    <ImeiCheckButton imei={order.device.imei} compact />
                  </span>
                ) : (
                  "—"
                )}
              </Field>
              <Field label="Serial">{order.device.serial_number ?? "—"}</Field>
              <Field label="Desbloqueo">{UNLOCK_LABELS[order.unlock_method]}</Field>
            </dl>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Gestión</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4">
            <AssignmentField order={order} />
            <dl className="grid grid-cols-[9rem_1fr] gap-x-4 gap-y-2">
              <Field label="Prioridad">{PRIORITY_LABELS[order.priority]}</Field>
              <Field label="Entrega estimada">{order.estimated_delivery_date ?? "—"}</Field>
              <Field label="Diagnóstico">{formatMoney(order.diagnostic_fee)}</Field>
              <Field label="Anticipo">
                {Number(order.advance_amount) > 0
                  ? `${formatMoney(order.advance_amount)} (${order.advance_method ? PAYMENT_LABELS[order.advance_method] : ""})`
                  : "Sin anticipo"}
              </Field>
              <Field label="Recibió">{order.received_by?.full_name ?? "—"}</Field>
              <Field label="Condiciones">Versión {order.terms_version}</Field>
              {order.delivered_at && (
                <Field label="Entregado">
                  {formatDateTime(order.delivered_at)} a {order.delivered_to_name}
                  {order.delivered_to_document ? ` (${order.delivered_to_document})` : ""}
                </Field>
              )}
            </dl>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recepción</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-x-4 gap-y-2 sm:grid-cols-[11rem_1fr]">
            <Field label="Falla reportada">{order.reported_issue}</Field>
            <Field label="Estado físico">{order.physical_condition}</Field>
            <Field label="Accesorios">{accessoriesText(order.accessories)}</Field>
            <Field label="Observaciones">{order.notes ?? "—"}</Field>
          </dl>
        </CardContent>
      </Card>

      {order.kind === "ASSEMBLY" ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ensamble</CardTitle>
          </CardHeader>
          <CardContent>
            <AssemblyChecklistPanel order={order} />
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Diagnóstico</CardTitle>
          </CardHeader>
          <CardContent>
            <DiagnosticPanel order={order} />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Cotización</CardTitle>
        </CardHeader>
        <CardContent>
          <QuotesPanel order={order} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Reparación y control de calidad</CardTitle>
        </CardHeader>
        <CardContent>
          <RepairPanel order={order} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Pagos</CardTitle>
        </CardHeader>
        <CardContent>
          <BillingPanel order={order} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Garantía</CardTitle>
        </CardHeader>
        <CardContent>
          <WarrantyPanel order={order} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Fotos del equipo</CardTitle>
        </CardHeader>
        <CardContent>
          <PhotoGallery order={order} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Historial</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="relative grid gap-4 border-l pl-5">
            {[...order.history].reverse().map((item, index) => (
              <li key={`${item.changed_at}-${index}`} className="relative">
                <span className="bg-primary absolute top-1.5 -left-[1.6rem] size-2.5 rounded-full" />
                <p className="text-sm font-medium">{STATUS_LABELS[item.to_status]}</p>
                <p className="text-muted-foreground text-xs">
                  {formatDateTime(item.changed_at)} · {item.changed_by?.full_name ?? "—"}
                </p>
                {item.reason && <p className="mt-1 text-sm whitespace-pre-wrap">{item.reason}</p>}
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>

      {target && (
        <StatusChangeDialog order={order} target={target} onClose={() => setTarget(null)} />
      )}
      {delivering && <DeliveryDialog order={order} onClose={() => setDelivering(false)} />}
    </>
  );
}

function AssignmentField({ order }: { order: WorkOrder }) {
  const canAssign = useCan(PERMS.WORK_ORDERS_ASSIGN);
  const technicians = useTechnicians(canAssign);
  const assign = useAssign();
  const closed = order.status === "ENTREGADO";

  if (!canAssign || closed) {
    return (
      <dl className="grid grid-cols-[9rem_1fr] gap-x-4">
        <Field label="Técnico">{order.assigned_technician?.full_name ?? "Sin asignar"}</Field>
      </dl>
    );
  }
  return (
    <SelectField
      label="Técnico asignado"
      value={order.assigned_technician?.id ?? ""}
      emptyLabel="Sin asignar"
      options={(technicians.data ?? []).map((t) => ({ value: t.id, label: t.full_name }))}
      disabled={assign.isPending}
      onChange={(technicianId) =>
        void assign
          .mutateAsync({ id: order.id, technicianId: technicianId || null })
          .then(() => toast.success("Técnico asignado."))
          .catch((error: unknown) => toast.error(errorMessage(error)))
      }
    />
  );
}
