import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, AlertTriangle, Plus, Search } from "lucide-react";
import { useDeferredValue, useMemo, useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";

import { FormField } from "@/components/FormField";
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
import { Textarea } from "@/components/ui/textarea";
import { formatPhone } from "@/lib/format";
import { PERMS, useCan } from "@/modules/auth/permissions";
import { CustomerFormDialog } from "@/modules/customers/components/CustomerFormDialog";
import { useCustomers } from "@/modules/customers/hooks";
import { formatDocument } from "@/modules/customers/presentation";
import { formatMoney } from "@/modules/workorders/presentation";
import { getProblem, errorMessage } from "@/services/errors";
import type {
  AgendaOptions,
  AppointmentCreate,
  AppointmentRead,
  AppointmentUpdate,
  ConsentChannelCode,
  PersonRef,
} from "@/types/api";

import { useCreateAppointment, useUpdateAppointment } from "../hooks";
import {
  bogotaDate,
  bogotaTime,
  CONSENT_CHANNEL_LABELS,
  durationLabel,
  hoursLabel,
  MODALITY_LABELS,
  toBogotaIso,
  weekdayOf,
} from "../presentation";
import { appointmentSchema, type AppointmentValues } from "../schemas";

interface AppointmentFormDialogProps {
  options: AgendaOptions;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Editing an existing appointment; otherwise a new one. */
  appointment?: AppointmentRead;
  /** Suggested date for a new appointment (YYYY-MM-DD). */
  initialDate?: string;
  /** Called with the saved appointment (e.g. to show its week). */
  onSaved?: (appointment: AppointmentRead) => void;
}

export function AppointmentFormDialog({
  options,
  open,
  onOpenChange,
  appointment,
  initialDate,
  onSaved,
}: AppointmentFormDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        {open && (
          <FormBody
            options={options}
            appointment={appointment}
            initialDate={initialDate}
            onDone={(saved) => {
              if (saved) onSaved?.(saved);
              onOpenChange(false);
            }}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

interface Overlap {
  detail: string;
  reason: string;
}

function FormBody({
  options,
  appointment,
  initialDate,
  onDone,
}: {
  options: AgendaOptions;
  appointment?: AppointmentRead;
  initialDate?: string;
  onDone: (saved?: AppointmentRead) => void;
}) {
  const isEdit = Boolean(appointment);
  const [customer, setCustomer] = useState<{ id: string; full_name: string } | null>(
    appointment ? appointment.customer : null,
  );
  const [serverError, setServerError] = useState<string | null>(null);
  const [overlap, setOverlap] = useState<Overlap | null>(null);
  const create = useCreateAppointment();
  const update = useUpdateAppointment();

  // In edit mode the service cannot change; it may be inactive now, so it is listed anyway.
  const services = useMemo(() => {
    if (!appointment || options.services.some((s) => s.id === appointment.service.id)) {
      return options.services;
    }
    return [
      ...options.services,
      {
        ...appointment.service,
        modality: appointment.modality,
        duration_minutes: appointment.duration_minutes,
        description: null,
        is_active: false,
      },
    ];
  }, [appointment, options.services]);
  const modalityOf = (id: string) => services.find((s) => s.id === id)?.modality;

  const {
    register,
    control,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<AppointmentValues>({
    resolver: zodResolver(appointmentSchema(modalityOf)),
    defaultValues: appointment
      ? {
          service_id: appointment.service.id,
          date: bogotaDate(appointment.starts_at),
          time: bogotaTime(appointment.starts_at),
          duration: String(appointment.duration_minutes),
          technician_id: appointment.technician?.id ?? "",
          reason: appointment.reason,
          address: appointment.address ?? "",
          locality: appointment.locality ?? "",
          notes: appointment.notes ?? "",
          consent_channel: appointment.remote_consent_channel ?? "",
        }
      : {
          service_id: services.length === 1 ? (services[0]?.id ?? "") : "",
          date: initialDate ?? "",
          time: "",
          duration: services.length === 1 ? String(services[0]?.duration_minutes ?? 60) : "60",
          technician_id: "",
          reason: "",
          address: "",
          locality: "",
          notes: "",
          consent_channel: "",
        },
  });
  const serviceId = useWatch({ control, name: "service_id" });
  const date = useWatch({ control, name: "date" });
  const service = services.find((s) => s.id === serviceId);
  const modality = service?.modality;
  const dayHours = date ? options.hours[weekdayOf(date)] : undefined;

  const save = async (values: AppointmentValues, overlapReason: string | null) => {
    setServerError(null);
    const common = {
      starts_at: toBogotaIso(values.date, values.time),
      duration_minutes: Number(values.duration),
      technician_id: values.technician_id || null,
      reason: values.reason,
      notes: values.notes || null,
      overlap_reason: overlapReason,
      ...(modality === "ON_SITE" ? { address: values.address, locality: values.locality } : {}),
    };
    try {
      let saved: AppointmentRead;
      if (appointment) {
        const data: AppointmentUpdate = common;
        saved = await update.mutateAsync({ id: appointment.id, data });
        toast.success(`Cita ${saved.number} actualizada.`);
      } else {
        if (!customer) {
          setServerError("Elija el cliente.");
          return;
        }
        const data: AppointmentCreate = {
          ...common,
          customer_id: customer.id,
          service_id: values.service_id,
          remote_consent_channel:
            modality === "REMOTE" ? (values.consent_channel as ConsentChannelCode) : null,
        };
        saved = await create.mutateAsync(data);
        toast.success(`Cita ${saved.number} agendada.`);
      }
      onDone(saved);
    } catch (error) {
      const problem = getProblem(error);
      if (problem?.code === "appointment_overlap") {
        setOverlap({ detail: problem.detail, reason: overlapReason ?? "" });
      } else {
        setServerError(errorMessage(error));
      }
    }
  };

  const onSubmit = handleSubmit((values) => save(values, null));
  const onForce = handleSubmit((values) => save(values, overlap?.reason.trim() || null));

  return (
    <>
      <DialogHeader>
        <DialogTitle>{isEdit ? `Editar cita ${appointment?.number}` : "Nueva cita"}</DialogTitle>
        <DialogDescription>
          Atención remota o en sitio, dentro del horario de servicio y sin festivos.
        </DialogDescription>
      </DialogHeader>
      <form onSubmit={onSubmit} className="grid gap-4" noValidate>
        {serverError && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>{serverError}</AlertDescription>
          </Alert>
        )}

        {isEdit ? (
          <p className="text-sm">
            <span className="text-muted-foreground">Cliente: </span>
            <span className="font-medium">{customer?.full_name}</span>
            <span className="text-muted-foreground"> · Servicio: </span>
            <span className="font-medium">{service?.name}</span>
          </p>
        ) : (
          <>
            <CustomerPicker customer={customer} onSelect={setCustomer} />
            <Controller
              control={control}
              name="service_id"
              render={({ field }) => (
                <SelectField
                  label="Servicio"
                  value={field.value}
                  onChange={(id) => {
                    field.onChange(id);
                    const chosen = services.find((s) => s.id === id);
                    if (chosen) setValue("duration", String(chosen.duration_minutes));
                  }}
                  placeholder="Elija el servicio"
                  options={services.map((s) => ({
                    value: s.id,
                    label: `${s.name} · ${MODALITY_LABELS[s.modality]}`,
                  }))}
                  error={errors.service_id?.message}
                />
              )}
            />
            {service && (
              <p className="text-muted-foreground -mt-2 text-xs">
                {MODALITY_LABELS[service.modality]} · {durationLabel(service.duration_minutes)} ·{" "}
                {service.price === null
                  ? "precio según el diagnóstico"
                  : `${formatMoney(service.price)}${service.tax_rate ? (service.price_includes_tax ? " IVA incluido" : " + IVA") : ""}`}
                {service.description ? ` · ${service.description}` : ""}
              </p>
            )}
          </>
        )}

        <div className="grid gap-4 sm:grid-cols-3">
          <FormField
            label="Fecha"
            type="date"
            error={errors.date?.message}
            hint={date ? `Horario: ${hoursLabel(dayHours)}` : undefined}
            {...register("date")}
          />
          <FormField
            label="Hora"
            type="time"
            step={300}
            error={errors.time?.message}
            {...register("time")}
          />
          <FormField
            label="Duración (minutos)"
            inputMode="numeric"
            error={errors.duration?.message}
            {...register("duration")}
          />
        </div>

        <Controller
          control={control}
          name="technician_id"
          render={({ field }) => (
            <SelectField
              label="Técnico"
              value={field.value}
              onChange={field.onChange}
              emptyLabel="Sin asignar"
              options={options.technicians.map((t: PersonRef) => ({
                value: t.id,
                label: t.full_name,
              }))}
            />
          )}
        />

        <div className="grid gap-1.5">
          <Label htmlFor="appointment-reason">Qué necesita el cliente</Label>
          <Textarea
            id="appointment-reason"
            aria-invalid={errors.reason ? true : undefined}
            {...register("reason")}
          />
          {errors.reason && <p className="text-destructive text-xs">{errors.reason.message}</p>}
        </div>

        {modality === "ON_SITE" && (
          <div className="grid gap-4 sm:grid-cols-[2fr_1fr]">
            <FormField
              label="Dirección de la visita"
              placeholder="Calle, número, apartamento, indicaciones"
              error={errors.address?.message}
              {...register("address")}
            />
            <Controller
              control={control}
              name="locality"
              render={({ field }) => (
                <SelectField
                  label="Localidad"
                  value={field.value}
                  onChange={field.onChange}
                  placeholder="Elija la localidad"
                  options={options.localities.map((l) => ({ value: l, label: l }))}
                  error={errors.locality?.message}
                />
              )}
            />
          </div>
        )}

        {modality === "REMOTE" && !isEdit && (
          <div className="bg-muted/40 grid gap-3 rounded-md border p-3">
            <p className="text-sm font-medium">Autorización de acceso remoto</p>
            <p className="text-muted-foreground text-xs">{options.remote_access_text}</p>
            <Controller
              control={control}
              name="consent_channel"
              render={({ field }) => (
                <SelectField
                  label="El cliente la aceptó"
                  value={field.value}
                  onChange={field.onChange}
                  placeholder="Elija cómo la aceptó"
                  options={Object.entries(CONSENT_CHANNEL_LABELS).map(([value, label]) => ({
                    value,
                    label,
                  }))}
                  error={errors.consent_channel?.message}
                />
              )}
            />
          </div>
        )}

        <div className="grid gap-1.5">
          <Label htmlFor="appointment-notes">Notas internas (opcional)</Label>
          <Textarea id="appointment-notes" {...register("notes")} />
        </div>

        {overlap && (
          <Alert>
            <AlertTriangle />
            <AlertTitle>El técnico ya tiene otra cita</AlertTitle>
            <AlertDescription className="grid gap-2">
              <span>{overlap.detail}</span>
              <Label htmlFor="overlap-reason" className="text-foreground">
                Razón para agendar de todas formas
              </Label>
              <Input
                id="overlap-reason"
                value={overlap.reason}
                onChange={(e) => setOverlap({ ...overlap, reason: e.target.value })}
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="w-fit"
                disabled={overlap.reason.trim().length < 3 || isSubmitting}
                onClick={() => void onForce()}
              >
                Agendar de todas formas
              </Button>
            </AlertDescription>
          </Alert>
        )}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onDone()}>
            Cerrar
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isEdit ? "Guardar cambios" : "Agendar cita"}
          </Button>
        </DialogFooter>
      </form>
    </>
  );
}

function CustomerPicker({
  customer,
  onSelect,
}: {
  customer: { id: string; full_name: string } | null;
  onSelect: (customer: { id: string; full_name: string } | null) => void;
}) {
  const canCreate = useCan(PERMS.CUSTOMERS_MANAGE);
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const query = useDeferredValue(search.trim());
  const results = useCustomers({ page: 1, size: 5, q: query || undefined, is_active: true });

  if (customer) {
    return (
      <div className="flex items-center justify-between gap-3 rounded-md border p-3">
        <div>
          <p className="text-muted-foreground text-xs">Cliente</p>
          <p className="font-medium">{customer.full_name}</p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={() => onSelect(null)}>
          Cambiar
        </Button>
      </div>
    );
  }
  return (
    <div className="grid gap-2">
      <Label htmlFor="appointment-customer">Cliente</Label>
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="text-muted-foreground absolute top-2.5 left-2.5 size-4" />
          <Input
            id="appointment-customer"
            className="pl-8"
            placeholder="Buscar por nombre, documento o teléfono"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        {canCreate && (
          <Button type="button" variant="outline" onClick={() => setCreating(true)}>
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
                onClick={() => onSelect({ id: c.id, full_name: c.full_name })}
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
      {creating && (
        <CustomerFormDialog
          open
          onOpenChange={setCreating}
          onCreated={(c) => onSelect({ id: c.id, full_name: c.full_name })}
        />
      )}
    </div>
  );
}
