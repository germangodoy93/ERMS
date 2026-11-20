import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  Eraser,
  MoreHorizontal,
  Pencil,
  Plus,
  Power,
} from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router";
import { toast } from "sonner";

import { StatusBadge } from "@/components/StatusBadge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatDateTime, formatPhone } from "@/lib/format";
import { PERMS, useCan } from "@/modules/auth/permissions";
import { DeviceFormDialog } from "@/modules/devices/components/DeviceFormDialog";
import { useCustomerDevices } from "@/modules/devices/hooks";
import { errorMessage } from "@/services/errors";
import type { Customer, Device } from "@/types/api";
import { ImeiCheckButton } from "@/modules/devices/components/ImeiCheckButton";

import {
  AnonymizeDialog,
  ConsentChangeDialog,
  type ConsentAction,
} from "../components/ConsentDialogs";
import { CustomerFormDialog } from "../components/CustomerFormDialog";
import { useConsentHistory, useCustomer, useUpdateCustomer } from "../hooks";
import {
  CHANNEL_LABELS,
  consentRows,
  customerState,
  formatDocument,
  ID_TYPE_LABELS,
  KIND_LABELS,
  PURPOSE_LABELS,
  STATE_BADGES,
} from "../presentation";

export function CustomerDetailPage() {
  const { customerId = "" } = useParams();
  const customer = useCustomer(customerId);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <Link
        to="/clientes"
        className="text-muted-foreground hover:text-foreground flex w-fit items-center gap-1 text-sm"
      >
        <ArrowLeft className="size-4" /> Clientes
      </Link>
      {customer.isPending && <Skeleton className="h-64" />}
      {customer.isError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{errorMessage(customer.error)}</AlertDescription>
        </Alert>
      )}
      {customer.data && <CustomerDetail customer={customer.data} />}
    </div>
  );
}

function CustomerDetail({ customer }: { customer: Customer }) {
  const canManage = useCan(PERMS.CUSTOMERS_MANAGE);
  const canAnonymize = useCan(PERMS.CUSTOMERS_ANONYMIZE);
  const update = useUpdateCustomer();
  const [editing, setEditing] = useState(false);
  const [anonymizing, setAnonymizing] = useState(false);
  const state = customerState(customer);
  const badge = STATE_BADGES[state];
  const anonymized = state === "anonymized";

  const toggleActive = async () => {
    try {
      await update.mutateAsync({ id: customer.id, changes: { is_active: !customer.is_active } });
      toast.success(customer.is_active ? "Cliente desactivado." : "Cliente activado.");
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };

  return (
    <>
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight">{customer.full_name}</h1>
            <StatusBadge tone={badge.tone} label={badge.label} />
          </div>
          <p className="text-muted-foreground text-sm">
            {KIND_LABELS[customer.kind]} · {formatDocument(customer)} · Cliente desde{" "}
            {formatDateTime(customer.created_at)}
          </p>
        </div>
        {!anonymized && (canManage || canAnonymize) && (
          <div className="flex gap-2">
            {canManage && (
              <Button variant="outline" onClick={() => setEditing(true)}>
                <Pencil /> Editar
              </Button>
            )}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="icon" aria-label="Más acciones">
                  <MoreHorizontal />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {canManage && (
                  <DropdownMenuItem onSelect={() => void toggleActive()}>
                    <Power /> {customer.is_active ? "Desactivar" : "Activar"}
                  </DropdownMenuItem>
                )}
                {canAnonymize && (
                  <DropdownMenuItem
                    className="text-destructive"
                    onSelect={() => setAnonymizing(true)}
                  >
                    <Eraser /> Anonimizar (supresión)
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}
      </header>

      {state === "no_consent" && (
        <Alert variant="destructive">
          <AlertTriangle />
          <AlertTitle>Sin autorización de tratamiento de datos</AlertTitle>
          <AlertDescription>
            No se pueden registrar equipos ni órdenes hasta registrar una nueva autorización.
          </AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="devices">
        <TabsList>
          <TabsTrigger value="devices">Equipos</TabsTrigger>
          <TabsTrigger value="data">Datos</TabsTrigger>
          <TabsTrigger value="consents">Autorizaciones</TabsTrigger>
        </TabsList>
        <TabsContent value="devices">
          <DevicesTab customer={customer} />
        </TabsContent>
        <TabsContent value="data">
          <DataTab customer={customer} />
        </TabsContent>
        <TabsContent value="consents">
          <ConsentsTab customer={customer} />
        </TabsContent>
      </Tabs>

      {editing && <CustomerFormDialog open customer={customer} onOpenChange={setEditing} />}
      <AnonymizeDialog
        key={String(anonymizing)}
        customer={customer}
        open={anonymizing}
        onClose={() => setAnonymizing(false)}
      />
    </>
  );
}

function DataTab({ customer }: { customer: Customer }) {
  const rows: [string, string][] = [
    ["Tipo", KIND_LABELS[customer.kind]],
    [
      "Documento",
      customer.id_type && customer.id_number
        ? `${ID_TYPE_LABELS[customer.id_type]} ${customer.id_number}`
        : "—",
    ],
    ["Teléfono", formatPhone(customer.phone)],
    ["Correo", customer.email ?? "—"],
    ["Dirección", customer.address ?? "—"],
    ["Notas", customer.notes ?? "—"],
    ["Última actualización", formatDateTime(customer.updated_at)],
  ];
  return (
    <dl className="grid gap-x-6 gap-y-3 rounded-lg border p-4 sm:grid-cols-[12rem_1fr]">
      {rows.map(([label, value]) => (
        <div key={label} className="contents">
          <dt className="text-muted-foreground text-sm">{label}</dt>
          <dd className="text-sm whitespace-pre-wrap">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function DevicesTab({ customer }: { customer: Customer }) {
  const canManage = useCan(PERMS.DEVICES_MANAGE);
  const devices = useCustomerDevices(customer.id);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Device | null>(null);

  return (
    <div className="grid gap-3">
      {canManage && customer.can_be_served && (
        <div className="flex justify-end">
          <Button onClick={() => setCreating(true)}>
            <Plus /> Registrar equipo
          </Button>
        </div>
      )}
      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Equipo</TableHead>
              <TableHead className="hidden sm:table-cell">IMEI / Serial</TableHead>
              <TableHead className="hidden md:table-cell">Detalles</TableHead>
              <TableHead className="w-12">
                <span className="sr-only">Acciones</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {devices.isPending && (
              <TableRow>
                <TableCell colSpan={4}>
                  <Skeleton className="h-6" />
                </TableCell>
              </TableRow>
            )}
            {devices.isError && (
              <TableRow>
                <TableCell colSpan={4} className="text-destructive py-6 text-center">
                  {errorMessage(devices.error)}
                </TableCell>
              </TableRow>
            )}
            {devices.data?.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="text-muted-foreground py-6 text-center">
                  Este cliente no tiene equipos registrados.
                </TableCell>
              </TableRow>
            )}
            {devices.data?.map((device) => (
              <TableRow key={device.id}>
                <TableCell>
                  <div className="font-medium">
                    {device.model.manufacturer.name} {device.model.name}
                  </div>
                  <div className="text-muted-foreground text-xs">{device.model.category.name}</div>
                </TableCell>
                <TableCell className="hidden font-mono text-xs sm:table-cell">
                  {device.imei && (
                    <div className="flex flex-col items-start gap-1">
                      <span>IMEI {device.imei}</span>
                      <ImeiCheckButton imei={device.imei} compact />
                    </div>
                  )}
                  {device.serial_number && <div>S/N {device.serial_number}</div>}
                  {!device.imei && !device.serial_number && "—"}
                </TableCell>
                <TableCell className="text-muted-foreground hidden text-sm md:table-cell">
                  {[device.operating_system, device.storage, device.color]
                    .filter(Boolean)
                    .join(" · ") || "—"}
                </TableCell>
                <TableCell>
                  {canManage && (
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Editar ${device.model.name}`}
                      onClick={() => setEditing(device)}
                    >
                      <Pencil />
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      {creating && <DeviceFormDialog open customerId={customer.id} onOpenChange={setCreating} />}
      {editing && (
        <DeviceFormDialog
          key={editing.id}
          open
          customerId={customer.id}
          device={editing}
          onOpenChange={(open) => !open && setEditing(null)}
        />
      )}
    </div>
  );
}

function ConsentsTab({ customer }: { customer: Customer }) {
  const canManage = useCan(PERMS.CUSTOMERS_MANAGE);
  const history = useConsentHistory(customer.id);
  const [action, setAction] = useState<ConsentAction | null>(null);
  const editable = canManage && !customer.anonymized_at;

  return (
    <div className="grid gap-6">
      <div className="grid gap-3 sm:grid-cols-3">
        {consentRows(customer.consents).map(({ purpose, status }) => (
          <div key={purpose} className="flex flex-col gap-2 rounded-lg border p-4">
            <p className="text-sm font-medium">{PURPOSE_LABELS[purpose]}</p>
            {status?.granted ? (
              <StatusBadge tone="success" label="Autorizada" />
            ) : (
              <StatusBadge
                tone={status ? "danger" : "neutral"}
                label={status ? "Revocada" : "No otorgada"}
              />
            )}
            {status && (
              <p className="text-muted-foreground text-xs">
                {CHANNEL_LABELS[status.channel]} · {formatDateTime(status.recorded_at)} · Política v
                {status.policy_version}
              </p>
            )}
            {editable && (
              <Button
                variant="outline"
                size="sm"
                className="mt-auto"
                onClick={() => setAction({ purpose, granted: !status?.granted })}
              >
                {status?.granted ? "Revocar" : "Otorgar"}
              </Button>
            )}
          </div>
        ))}
      </div>

      <section className="grid gap-2">
        <h2 className="text-sm font-medium">Historial</h2>
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Fecha</TableHead>
                <TableHead>Finalidad</TableHead>
                <TableHead>Acción</TableHead>
                <TableHead className="hidden md:table-cell">Medio</TableHead>
                <TableHead className="hidden md:table-cell">Registró</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {history.data?.map((record) => (
                <TableRow key={record.id}>
                  <TableCell className="text-sm">{formatDateTime(record.recorded_at)}</TableCell>
                  <TableCell className="text-sm">{PURPOSE_LABELS[record.purpose]}</TableCell>
                  <TableCell className="text-sm">
                    {record.granted ? "Otorgada" : "Revocada"} (v{record.policy_version})
                  </TableCell>
                  <TableCell className="hidden text-sm md:table-cell">
                    {CHANNEL_LABELS[record.channel]}
                  </TableCell>
                  <TableCell className="text-muted-foreground hidden text-sm md:table-cell">
                    {record.recorded_by ?? "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </section>

      <ConsentChangeDialog
        key={action ? `${action.purpose}-${action.granted}` : "none"}
        customer={customer}
        action={action}
        onClose={() => setAction(null)}
      />
    </div>
  );
}
