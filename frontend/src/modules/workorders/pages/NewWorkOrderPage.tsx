import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, AlertTriangle, ArrowLeft, Check, Plus, Search } from "lucide-react";
import { useDeferredValue, useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { Link, useNavigate } from "react-router";
import { toast } from "sonner";

import { FormField } from "@/components/FormField";
import { SelectField } from "@/components/SelectField";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { saveBlob } from "@/lib/download";
import { formatPhone } from "@/lib/format";
import { cn } from "@/lib/utils";
import { PERMS, useCan } from "@/modules/auth/permissions";
import { CustomerFormDialog } from "@/modules/customers/components/CustomerFormDialog";
import { useCustomer, useCustomers } from "@/modules/customers/hooks";
import { formatDocument } from "@/modules/customers/presentation";
import { DeviceFormDialog } from "@/modules/devices/components/DeviceFormDialog";
import { useCustomerDevices } from "@/modules/devices/hooks";
import { errorMessage } from "@/services/errors";
import {
  ACCESSORIES,
  PAYMENT_METHODS,
  PRIORITIES,
  UNLOCK_METHODS,
  type AccessoryItem,
  type WorkOrderCreate,
} from "@/types/api";

import { downloadReceptionAct } from "../api";
import { useCreateWorkOrder, useReceptionTerms, useTechnicians } from "../hooks";
import {
  ACCESSORY_LABELS,
  parseMoney,
  PAYMENT_LABELS,
  PRIORITY_LABELS,
  todayInBogota,
  UNLOCK_LABELS,
} from "../presentation";
import { receptionSchema, type ReceptionValues } from "../schemas";

export function NewWorkOrderPage() {
  const terms = useReceptionTerms();
  const [customerId, setCustomerId] = useState<string | null>(null);
  const [deviceId, setDeviceId] = useState<string | null>(null);

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
      <Link
        to="/ordenes"
        className="text-muted-foreground hover:text-foreground flex w-fit items-center gap-1 text-sm"
      >
        <ArrowLeft className="size-4" /> Órdenes de servicio
      </Link>
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Nueva recepción</h1>
        <p className="text-muted-foreground text-sm">
          Al guardar se genera el número de orden y se descarga el acta para que el cliente la
          firme.
        </p>
      </header>

      {terms.data && !terms.data.terms && <NoTermsNotice />}

      <CustomerStep
        customerId={customerId}
        onSelect={(id) => {
          setCustomerId(id);
          setDeviceId(null);
        }}
      />
      {customerId && (
        <DeviceStep customerId={customerId} deviceId={deviceId} onSelect={setDeviceId} />
      )}
      {customerId && deviceId && terms.data?.terms && (
        <ReceptionForm customerId={customerId} deviceId={deviceId} />
      )}
    </div>
  );
}

function NoTermsNotice() {
  const canPublish = useCan(PERMS.ORGANIZATION_MANAGE);
  return (
    <Alert variant="destructive">
      <AlertTriangle />
      <AlertTitle>Faltan las condiciones del acta de recepción</AlertTitle>
      <AlertDescription>
        {canPublish ? (
          <span>
            Publíquelas en{" "}
            <Link to="/taller" className="underline">
              Datos del taller
            </Link>{" "}
            antes de recibir equipos.
          </span>
        ) : (
          "Un administrador debe publicarlas antes de recibir equipos."
        )}
      </AlertDescription>
    </Alert>
  );
}

function StepCard({
  step,
  title,
  done,
  children,
}: {
  step: number;
  title: string;
  done: boolean;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <span
            className={cn(
              "grid size-6 place-items-center rounded-full text-xs",
              done ? "bg-success text-white" : "bg-muted text-muted-foreground",
            )}
          >
            {done ? <Check className="size-3.5" /> : step}
          </span>
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function CustomerStep({
  customerId,
  onSelect,
}: {
  customerId: string | null;
  onSelect: (id: string | null) => void;
}) {
  const canCreate = useCan(PERMS.CUSTOMERS_MANAGE);
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const query = useDeferredValue(search.trim());
  const results = useCustomers({ page: 1, size: 6, q: query || undefined, is_active: true });
  const selected = useCustomer(customerId ?? "");

  if (customerId) {
    const customer = selected.data;
    return (
      <StepCard step={1} title="Cliente" done={Boolean(customer?.can_be_served)}>
        {!customer ? (
          <Skeleton className="h-12" />
        ) : (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-medium">{customer.full_name}</p>
              <p className="text-muted-foreground text-sm">
                {formatDocument(customer)} · {formatPhone(customer.phone)}
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={() => onSelect(null)}>
              Cambiar
            </Button>
            {!customer.can_be_served && (
              <Alert variant="destructive" className="w-full">
                <AlertCircle />
                <AlertDescription>
                  El cliente no tiene autorización de datos vigente o está inactivo. Revise su{" "}
                  <Link to={`/clientes/${customer.id}`} className="underline">
                    ficha
                  </Link>
                  .
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}
      </StepCard>
    );
  }

  return (
    <StepCard step={1} title="Cliente" done={false}>
      <div className="grid gap-3">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="text-muted-foreground absolute top-2.5 left-2.5 size-4" />
            <Input
              className="pl-8"
              placeholder="Buscar por nombre, documento o teléfono"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Buscar cliente"
            />
          </div>
          {canCreate && (
            <Button variant="outline" onClick={() => setCreating(true)}>
              <Plus /> Nuevo cliente
            </Button>
          )}
        </div>
        {query && (
          <ul className="divide-y rounded-md border">
            {results.data?.items.length === 0 && (
              <li className="text-muted-foreground p-3 text-sm">Sin resultados.</li>
            )}
            {results.data?.items.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  className="hover:bg-muted/60 flex w-full items-center justify-between gap-3 p-3 text-left text-sm"
                  onClick={() => onSelect(c.id)}
                >
                  <span className="font-medium">{c.full_name}</span>
                  <span className="text-muted-foreground">
                    {formatDocument(c)} · {formatPhone(c.phone)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      {creating && (
        <CustomerFormDialog open onOpenChange={setCreating} onCreated={(c) => onSelect(c.id)} />
      )}
    </StepCard>
  );
}

function DeviceStep({
  customerId,
  deviceId,
  onSelect,
}: {
  customerId: string;
  deviceId: string | null;
  onSelect: (id: string) => void;
}) {
  const canRegister = useCan(PERMS.DEVICES_MANAGE);
  const customer = useCustomer(customerId);
  const devices = useCustomerDevices(customerId);
  const [creating, setCreating] = useState(false);
  const active = devices.data?.filter((d) => d.is_active) ?? [];

  if (!customer.data?.can_be_served) return null;

  return (
    <StepCard step={2} title="Equipo" done={Boolean(deviceId)}>
      <div className="grid gap-2">
        {devices.isPending && <Skeleton className="h-12" />}
        {devices.data && active.length === 0 && (
          <p className="text-muted-foreground text-sm">El cliente no tiene equipos registrados.</p>
        )}
        <div role="radiogroup" aria-label="Equipo" className="grid gap-2 sm:grid-cols-2">
          {active.map((device) => (
            <button
              key={device.id}
              type="button"
              role="radio"
              aria-checked={device.id === deviceId}
              onClick={() => onSelect(device.id)}
              className={cn(
                "rounded-md border p-3 text-left text-sm transition-colors",
                device.id === deviceId ? "border-primary bg-primary/5" : "hover:bg-muted/60",
              )}
            >
              <div className="font-medium">
                {device.model.manufacturer.name} {device.model.name}
              </div>
              <div className="text-muted-foreground font-mono text-xs">
                {device.imei
                  ? `IMEI ${device.imei}`
                  : device.serial_number
                    ? `S/N ${device.serial_number}`
                    : device.model.category.name}
              </div>
            </button>
          ))}
        </div>
        {canRegister && (
          <Button variant="outline" className="w-fit" onClick={() => setCreating(true)}>
            <Plus /> Registrar otro equipo
          </Button>
        )}
      </div>
      {creating && (
        <DeviceFormDialog
          open
          customerId={customerId}
          onOpenChange={setCreating}
          onCreated={(device) => onSelect(device.id)}
        />
      )}
    </StepCard>
  );
}

function ReceptionForm({ customerId, deviceId }: { customerId: string; deviceId: string }) {
  const navigate = useNavigate();
  const canAssign = useCan(PERMS.WORK_ORDERS_ASSIGN);
  const technicians = useTechnicians(canAssign);
  const create = useCreateWorkOrder();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ReceptionValues>({
    resolver: zodResolver(receptionSchema),
    defaultValues: {
      reported_issue: "",
      physical_condition: "",
      accessories: [],
      other_accessory: "",
      unlock_method: "NOT_REQUIRED",
      priority: "NORMAL",
      estimated_delivery_date: "",
      diagnostic_fee: "",
      advance_amount: "",
      advance_method: "",
      technician_id: "",
      notes: "",
    },
  });
  const accessories = useWatch({ control, name: "accessories" });

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    const items: AccessoryItem[] = values.accessories.map((code) =>
      code === "OTHER" ? { code, detail: values.other_accessory } : { code },
    );
    const advance = parseMoney(values.advance_amount) ?? "0.00";
    const payload: WorkOrderCreate = {
      customer_id: customerId,
      device_id: deviceId,
      reported_issue: values.reported_issue,
      physical_condition: values.physical_condition,
      accessories: items,
      unlock_method: values.unlock_method,
      priority: values.priority,
      estimated_delivery_date: values.estimated_delivery_date || null,
      diagnostic_fee: parseMoney(values.diagnostic_fee) ?? "0.00",
      advance_amount: advance,
      advance_method: Number(advance) > 0 && values.advance_method ? values.advance_method : null,
      notes: values.notes || null,
      assigned_technician_id: values.technician_id || null,
    };
    try {
      const order = await create.mutateAsync(payload);
      toast.success(`Orden ${order.number} creada.`);
      try {
        saveBlob(await downloadReceptionAct(order.id), `acta-${order.number}.pdf`);
      } catch {
        toast.error("No se pudo descargar el acta. Descárguela desde el detalle de la orden.");
      }
      void navigate(`/ordenes/${order.id}`);
    } catch (error) {
      setServerError(errorMessage(error));
    }
  });

  return (
    <StepCard step={3} title="Recepción del equipo" done={false}>
      <form onSubmit={onSubmit} className="grid gap-4" noValidate>
        {serverError && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>{serverError}</AlertDescription>
          </Alert>
        )}
        <div className="grid gap-1.5">
          <Label htmlFor="reported-issue">Falla reportada por el cliente</Label>
          <Textarea
            id="reported-issue"
            aria-invalid={errors.reported_issue ? true : undefined}
            {...register("reported_issue")}
          />
          {errors.reported_issue && (
            <p className="text-destructive text-xs">{errors.reported_issue.message}</p>
          )}
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="physical-condition">Estado físico (verificado con el cliente)</Label>
          <Textarea
            id="physical-condition"
            placeholder="Rayones, golpes, pantalla, tapa, puertos…"
            aria-invalid={errors.physical_condition ? true : undefined}
            {...register("physical_condition")}
          />
          {errors.physical_condition && (
            <p className="text-destructive text-xs">{errors.physical_condition.message}</p>
          )}
        </div>

        <fieldset className="grid gap-2">
          <legend className="mb-1 text-sm font-medium">Accesorios entregados</legend>
          <Controller
            control={control}
            name="accessories"
            render={({ field }) => (
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {ACCESSORIES.map((code) => (
                  <Label key={code} className="flex items-center gap-2 font-normal">
                    <Checkbox
                      checked={field.value.includes(code)}
                      onCheckedChange={(v) =>
                        field.onChange(
                          v ? [...field.value, code] : field.value.filter((c) => c !== code),
                        )
                      }
                    />
                    {ACCESSORY_LABELS[code]}
                  </Label>
                ))}
              </div>
            )}
          />
          {accessories.includes("OTHER") && (
            <FormField
              label="¿Cuál otro accesorio?"
              error={errors.other_accessory?.message}
              {...register("other_accessory")}
            />
          )}
        </fieldset>

        <div className="grid gap-4 sm:grid-cols-2">
          <Controller
            control={control}
            name="unlock_method"
            render={({ field }) => (
              <SelectField
                label="Desbloqueo (no se registran contraseñas)"
                value={field.value}
                onChange={field.onChange}
                options={UNLOCK_METHODS.map((m) => ({ value: m, label: UNLOCK_LABELS[m] }))}
              />
            )}
          />
          <Controller
            control={control}
            name="priority"
            render={({ field }) => (
              <SelectField
                label="Prioridad"
                value={field.value}
                onChange={field.onChange}
                options={PRIORITIES.map((p) => ({ value: p, label: PRIORITY_LABELS[p] }))}
              />
            )}
          />
          <FormField
            label="Valor del diagnóstico"
            inputMode="numeric"
            placeholder="0"
            error={errors.diagnostic_fee?.message}
            {...register("diagnostic_fee")}
          />
          <FormField
            label="Entrega estimada (opcional)"
            type="date"
            min={todayInBogota()}
            {...register("estimated_delivery_date")}
          />
          <FormField
            label="Anticipo recibido"
            inputMode="numeric"
            placeholder="0"
            error={errors.advance_amount?.message}
            {...register("advance_amount")}
          />
          <Controller
            control={control}
            name="advance_method"
            render={({ field }) => (
              <SelectField
                label="Medio de pago del anticipo"
                value={field.value}
                onChange={field.onChange}
                emptyLabel="Sin anticipo"
                options={PAYMENT_METHODS.map((m) => ({ value: m, label: PAYMENT_LABELS[m] }))}
                error={errors.advance_method?.message}
              />
            )}
          />
          {canAssign && (
            <Controller
              control={control}
              name="technician_id"
              render={({ field }) => (
                <SelectField
                  label="Técnico (opcional)"
                  value={field.value}
                  onChange={field.onChange}
                  emptyLabel="Sin asignar"
                  options={(technicians.data ?? []).map((t) => ({
                    value: t.id,
                    label: t.full_name,
                  }))}
                />
              )}
            />
          )}
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="order-notes">Observaciones (opcional)</Label>
          <Textarea id="order-notes" {...register("notes")} />
        </div>
        <div className="flex justify-end">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Guardando…" : "Crear orden y descargar acta"}
          </Button>
        </div>
      </form>
    </StepCard>
  );
}
