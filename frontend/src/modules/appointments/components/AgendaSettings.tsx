import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, Pencil, Plus } from "lucide-react";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";

import { FormField } from "@/components/FormField";
import { SelectField } from "@/components/SelectField";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import { formatMoney, parseMoney } from "@/modules/workorders/presentation";
import { errorMessage } from "@/services/errors";
import type { FieldService, HoursDay } from "@/types/api";

import {
  useFieldServices,
  useSaveFieldService,
  useSaveServiceHours,
  useServiceHours,
} from "../hooks";
import { durationLabel, MODALITY_LABELS, WEEKDAY_LABELS } from "../presentation";
import { fieldServiceSchema, type FieldServiceValues } from "../schemas";

export function ServiceHoursCard() {
  const hours = useServiceHours();
  return (
    <Card>
      <CardHeader>
        <CardTitle>Horario de servicio remoto y en sitio</CardTitle>
        <CardDescription>
          Independiente del horario del taller. No se puede agendar fuera de él ni en festivos de
          Colombia.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {hours.isPending && <Skeleton className="h-60" />}
        {hours.data && <HoursForm key={JSON.stringify(hours.data)} initial={hours.data.days} />}
      </CardContent>
    </Card>
  );
}

const hhmm = (value: string | null) => (value ? value.slice(0, 5) : "");

function HoursForm({ initial }: { initial: HoursDay[] }) {
  const [days, setDays] = useState(() =>
    initial.map((d) => ({ weekday: d.weekday, opens: hhmm(d.opens), closes: hhmm(d.closes) })),
  );
  const save = useSaveServiceHours();
  const change = (weekday: number, patch: Partial<{ opens: string; closes: string }>) =>
    setDays((current) => current.map((d) => (d.weekday === weekday ? { ...d, ...patch } : d)));

  const submit = async () => {
    try {
      await save.mutateAsync(
        days.map((d) => ({
          weekday: d.weekday,
          opens: d.opens && d.closes ? d.opens : null,
          closes: d.opens && d.closes ? d.closes : null,
        })),
      );
      toast.success("Horario guardado.");
    } catch (error) {
      toast.error(errorMessage(error, "No se pudo guardar el horario."));
    }
  };

  return (
    <div className="grid gap-3">
      {days.map((d) => {
        const open = Boolean(d.opens || d.closes);
        return (
          <div key={d.weekday} className="grid grid-cols-[7rem_auto_1fr_1fr] items-center gap-3">
            <span className="text-sm font-medium">{WEEKDAY_LABELS[d.weekday]}</span>
            <Label className="flex items-center gap-2 text-sm font-normal">
              <Checkbox
                checked={open}
                aria-label={`Hay servicio el ${WEEKDAY_LABELS[d.weekday]?.toLowerCase()}`}
                onCheckedChange={(v) =>
                  change(
                    d.weekday,
                    v ? { opens: "08:00", closes: "18:00" } : { opens: "", closes: "" },
                  )
                }
              />
              Servicio
            </Label>
            <Input
              type="time"
              step={300}
              aria-label={`Inicio ${WEEKDAY_LABELS[d.weekday]}`}
              value={d.opens}
              disabled={!open}
              onChange={(e) => change(d.weekday, { opens: e.target.value })}
            />
            <Input
              type="time"
              step={300}
              aria-label={`Fin ${WEEKDAY_LABELS[d.weekday]}`}
              value={d.closes}
              disabled={!open}
              onChange={(e) => change(d.weekday, { closes: e.target.value })}
            />
          </div>
        );
      })}
      <Button className="w-fit" onClick={() => void submit()} disabled={save.isPending}>
        Guardar horario
      </Button>
    </div>
  );
}

export function FieldServicesCard() {
  const services = useFieldServices();
  const [editing, setEditing] = useState<FieldService | "new" | null>(null);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Servicios remotos y en sitio</CardTitle>
        <CardDescription>
          Lo que se puede agendar. Sin precio, el valor se da después del diagnóstico.
        </CardDescription>
        <CardAction>
          <Button variant="outline" size="sm" onClick={() => setEditing("new")}>
            <Plus /> Nuevo servicio
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent>
        {services.isPending && <Skeleton className="h-24" />}
        <ul className="divide-y">
          {services.data?.map((s) => (
            <li key={s.id} className="flex items-start justify-between gap-3 py-3">
              <div className="grid gap-0.5">
                <p className="flex flex-wrap items-center gap-2 font-medium">
                  {s.name}
                  <Badge variant="outline">{MODALITY_LABELS[s.modality]}</Badge>
                  {!s.is_active && <Badge variant="secondary">Inactivo</Badge>}
                </p>
                <p className="text-muted-foreground text-sm">
                  {durationLabel(s.duration_minutes)} ·{" "}
                  {s.price === null ? "Precio según el diagnóstico" : formatMoney(s.price)}
                  {s.price !== null && s.tax_rate
                    ? s.price_includes_tax
                      ? " IVA incluido"
                      : " + IVA"
                    : ""}
                </p>
                {s.description && <p className="text-muted-foreground text-xs">{s.description}</p>}
              </div>
              <Button
                variant="ghost"
                size="icon"
                aria-label={`Editar ${s.name}`}
                onClick={() => setEditing(s)}
              >
                <Pencil />
              </Button>
            </li>
          ))}
        </ul>
      </CardContent>
      <Dialog open={editing !== null} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent className="sm:max-w-lg">
          {editing !== null && (
            <ServiceForm
              service={editing === "new" ? null : editing}
              onDone={() => setEditing(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </Card>
  );
}

function priceText(value: string | null): string {
  if (value === null) return "";
  return Number(value).toLocaleString("es-CO", { maximumFractionDigits: 2 });
}

function ServiceForm({ service, onDone }: { service: FieldService | null; onDone: () => void }) {
  const save = useSaveFieldService();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FieldServiceValues>({
    resolver: zodResolver(fieldServiceSchema),
    defaultValues: {
      name: service?.name ?? "",
      modality: service?.modality ?? "ON_SITE",
      duration_minutes: String(service?.duration_minutes ?? 60),
      price: priceText(service?.price ?? null),
      tax_rate: service?.tax_rate === 19 ? "19" : "0",
      price_includes_tax: service?.price_includes_tax ?? false,
      description: service?.description ?? "",
      is_active: service?.is_active ?? true,
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    try {
      await save.mutateAsync({
        id: service?.id ?? null,
        data: {
          name: values.name,
          modality: values.modality,
          duration_minutes: Number(values.duration_minutes),
          price: values.price ? parseMoney(values.price) : null,
          tax_rate: Number(values.tax_rate),
          price_includes_tax: values.price_includes_tax,
          description: values.description || null,
          is_active: values.is_active,
        },
      });
      toast.success("Servicio guardado.");
      onDone();
    } catch (error) {
      setServerError(errorMessage(error));
    }
  });

  return (
    <form onSubmit={onSubmit} className="grid gap-4" noValidate>
      <DialogHeader>
        <DialogTitle>{service ? "Editar servicio" : "Nuevo servicio"}</DialogTitle>
        <DialogDescription>Precios registrados por el taller.</DialogDescription>
      </DialogHeader>
      {serverError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{serverError}</AlertDescription>
        </Alert>
      )}
      <FormField label="Nombre" error={errors.name?.message} {...register("name")} />
      <div className="grid gap-4 sm:grid-cols-2">
        <Controller
          control={control}
          name="modality"
          render={({ field }) => (
            <SelectField
              label="Modalidad"
              value={field.value}
              onChange={field.onChange}
              options={Object.entries(MODALITY_LABELS).map(([value, label]) => ({
                value,
                label,
              }))}
            />
          )}
        />
        <FormField
          label="Duración (minutos)"
          inputMode="numeric"
          error={errors.duration_minutes?.message}
          {...register("duration_minutes")}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField
          label="Precio (opcional)"
          inputMode="decimal"
          placeholder="Vacío: según el diagnóstico"
          error={errors.price?.message}
          {...register("price")}
        />
        <Controller
          control={control}
          name="tax_rate"
          render={({ field }) => (
            <SelectField
              label="IVA"
              value={field.value}
              onChange={field.onChange}
              options={[
                { value: "0", label: "Sin IVA (0 %)" },
                { value: "19", label: "19 %" },
              ]}
            />
          )}
        />
      </div>
      <Controller
        control={control}
        name="price_includes_tax"
        render={({ field }) => (
          <Label className="flex items-center gap-2 font-normal">
            <Checkbox checked={field.value} onCheckedChange={(v) => field.onChange(v === true)} />
            El precio ya incluye el IVA
          </Label>
        )}
      />
      <div className="grid gap-1.5">
        <Label htmlFor="service-description">Descripción (opcional)</Label>
        <Textarea id="service-description" {...register("description")} />
      </div>
      <Controller
        control={control}
        name="is_active"
        render={({ field }) => (
          <Label className="flex items-center gap-2 font-normal">
            <Checkbox checked={field.value} onCheckedChange={(v) => field.onChange(v === true)} />
            Activo (se puede agendar)
          </Label>
        )}
      />
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onDone}>
          Cerrar
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          Guardar
        </Button>
      </DialogFooter>
    </form>
  );
}
