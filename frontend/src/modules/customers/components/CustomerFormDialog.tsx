import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, AlertTriangle } from "lucide-react";
import { useState } from "react";
import { Controller, useForm, type Control, type FieldPath } from "react-hook-form";
import { Link } from "react-router";
import { toast } from "sonner";

import { FormField } from "@/components/FormField";
import { SelectField } from "@/components/SelectField";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { PERMS, useCan } from "@/modules/auth/permissions";
import { useCurrentPolicy } from "@/modules/organization/hooks";
import { errorMessage } from "@/services/errors";
import {
  CONSENT_CHANNELS,
  CUSTOMER_KINDS,
  ID_TYPES,
  type ConsentGrant,
  type Customer,
  type CustomerUpdate,
} from "@/types/api";

import { useCreateCustomer, useUpdateCustomer } from "../hooks";
import { CHANNEL_LABELS, ID_TYPE_LABELS, KIND_LABELS, PURPOSE_LABELS } from "../presentation";
import {
  createCustomerSchema,
  editCustomerSchema,
  type CreateCustomerValues,
  type EditCustomerValues,
} from "../schemas";

const KIND_OPTIONS = CUSTOMER_KINDS.map((k) => ({ value: k, label: KIND_LABELS[k] }));
const ID_TYPE_OPTIONS = ID_TYPES.map((t) => ({ value: t, label: `${t} · ${ID_TYPE_LABELS[t]}` }));
const CHANNEL_OPTIONS = CONSENT_CHANNELS.map((c) => ({ value: c, label: CHANNEL_LABELS[c] }));

type Values = CreateCustomerValues | EditCustomerValues;

function emptyToNull(value: string): string | null {
  return value === "" ? null : value;
}

/** Create (customer = undefined) or edit a customer. */
export function CustomerFormDialog({
  open,
  onOpenChange,
  customer,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  customer?: Customer;
  onCreated?: (customer: Customer) => void;
}) {
  const isEdit = Boolean(customer);
  const createCustomer = useCreateCustomer();
  const updateCustomer = useUpdateCustomer();
  const policy = useCurrentPolicy();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(isEdit ? editCustomerSchema : createCustomerSchema),
    defaultValues: {
      kind: customer?.kind ?? "PERSON",
      full_name: customer?.full_name ?? "",
      id_type: customer?.id_type ?? "CC",
      id_number: customer?.id_number ?? "",
      phone: customer?.phone ?? "",
      email: customer?.email ?? "",
      address: customer?.address ?? "",
      notes: customer?.notes ?? "",
      ...(isEdit
        ? {}
        : { channel: "SCREEN", data_processing: false, photos: false, diagnostic_agent: false }),
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    const fields = {
      kind: values.kind,
      full_name: values.full_name,
      id_type: values.id_type === "" || !values.id_number ? null : values.id_type,
      id_number: emptyToNull(values.id_number),
      phone: emptyToNull(values.phone),
      email: emptyToNull(values.email),
      address: emptyToNull(values.address),
      notes: emptyToNull(values.notes),
    };
    try {
      if (customer) {
        const changes: CustomerUpdate = {};
        for (const [key, value] of Object.entries(fields) as [keyof typeof fields, unknown][]) {
          if (value !== customer[key]) Object.assign(changes, { [key]: value });
        }
        // The document type and number are validated together.
        if ("id_type" in changes || "id_number" in changes) {
          changes.id_type = fields.id_type;
          changes.id_number = fields.id_number;
        }
        await updateCustomer.mutateAsync({ id: customer.id, changes });
        toast.success("Cliente actualizado.");
      } else {
        const created = values as CreateCustomerValues;
        const consents: ConsentGrant[] = [{ purpose: "DATA_PROCESSING", channel: created.channel }];
        if (created.photos) consents.push({ purpose: "PHOTOS", channel: created.channel });
        if (created.diagnostic_agent) {
          consents.push({ purpose: "DIAGNOSTIC_AGENT", channel: created.channel });
        }
        const saved = await createCustomer.mutateAsync({ ...fields, consents });
        toast.success("Cliente registrado.");
        onCreated?.(saved);
      }
      onOpenChange(false);
    } catch (error) {
      setServerError(errorMessage(error));
    }
  });

  const noPolicy = !isEdit && policy.data && !policy.data.policy;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92dvh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Editar cliente" : "Nuevo cliente"}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Los cambios quedan registrados en la auditoría (sin los datos personales)."
              : "Se requiere la autorización del cliente para el tratamiento de sus datos."}
          </DialogDescription>
        </DialogHeader>

        {noPolicy ? (
          <NoPolicyNotice />
        ) : (
          <form onSubmit={onSubmit} className="grid gap-4" noValidate>
            {serverError && (
              <Alert variant="destructive">
                <AlertCircle />
                <AlertDescription>{serverError}</AlertDescription>
              </Alert>
            )}
            <div className="grid gap-4 sm:grid-cols-[10rem_1fr]">
              <Controller
                control={control}
                name="kind"
                render={({ field }) => (
                  <SelectField
                    label="Tipo"
                    value={field.value}
                    onChange={field.onChange}
                    options={KIND_OPTIONS}
                  />
                )}
              />
              <FormField
                label="Nombre o razón social"
                autoComplete="off"
                error={errors.full_name?.message}
                {...register("full_name")}
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Controller
                control={control}
                name="id_type"
                render={({ field }) => (
                  <SelectField
                    label="Tipo de documento"
                    value={field.value}
                    onChange={field.onChange}
                    options={ID_TYPE_OPTIONS}
                    emptyLabel="Sin documento"
                  />
                )}
              />
              <FormField
                label="Número de documento (opcional)"
                autoComplete="off"
                error={errors.id_number?.message}
                {...register("id_number")}
              />
              <FormField
                label="Teléfono"
                type="tel"
                autoComplete="off"
                placeholder="300 123 4567"
                error={errors.phone?.message}
                {...register("phone")}
              />
              <FormField
                label="Correo electrónico"
                type="email"
                autoComplete="off"
                error={errors.email?.message}
                {...register("email")}
              />
            </div>
            <FormField label="Dirección (opcional)" autoComplete="off" {...register("address")} />
            <div className="grid gap-1.5">
              <Label htmlFor="customer-notes">Notas (opcional)</Label>
              <Textarea
                id="customer-notes"
                placeholder="No registre contraseñas ni datos sensibles."
                {...register("notes")}
              />
            </div>

            {!isEdit && (
              <ConsentSection
                control={control}
                authorizations={policy.data?.authorizations}
                loading={policy.isPending}
                error={errors as Partial<Record<string, { message?: string }>>}
              />
            )}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Guardando…" : isEdit ? "Guardar cambios" : "Registrar cliente"}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}

function NoPolicyNotice() {
  const canPublish = useCan(PERMS.ORGANIZATION_MANAGE);
  return (
    <Alert variant="destructive">
      <AlertTriangle />
      <AlertTitle>Falta la política de tratamiento de datos</AlertTitle>
      <AlertDescription>
        {canPublish ? (
          <span>
            Publíquela en{" "}
            <Link to="/taller" className="underline">
              Datos del taller
            </Link>{" "}
            antes de registrar clientes.
          </span>
        ) : (
          "Un administrador debe publicarla antes de registrar clientes."
        )}
      </AlertDescription>
    </Alert>
  );
}

function ConsentSection({
  control,
  authorizations,
  loading,
  error,
}: {
  control: Control<Values>;
  authorizations: Partial<Record<string, string>> | undefined;
  loading: boolean;
  error: Partial<Record<string, { message?: string }>>;
}) {
  if (loading) return <Skeleton className="h-40" />;
  const purposes = [
    { name: "data_processing", purpose: "DATA_PROCESSING", required: true },
    { name: "photos", purpose: "PHOTOS", required: false },
    { name: "diagnostic_agent", purpose: "DIAGNOSTIC_AGENT", required: false },
  ] as const;

  return (
    <fieldset className="grid gap-3 rounded-md border p-4">
      <legend className="px-1 text-sm font-medium">Autorizaciones del cliente</legend>
      <p className="text-muted-foreground text-xs">
        Lea o muestre cada texto al cliente. Las autorizaciones opcionales se pueden otorgar más
        adelante.
      </p>
      {purposes.map(({ name, purpose, required }) => (
        <Controller
          key={name}
          control={control}
          name={name as FieldPath<Values>}
          render={({ field }) => (
            <div className="grid gap-1">
              <Label className="flex items-start gap-2 font-normal">
                <Checkbox
                  className="mt-0.5"
                  checked={field.value === true}
                  onCheckedChange={(v) => field.onChange(v === true)}
                />
                <span>
                  <span className="font-medium">
                    {PURPOSE_LABELS[purpose]}
                    {required ? " (obligatoria)" : " (opcional)"}
                  </span>
                  <span className="text-muted-foreground mt-1 block text-xs leading-relaxed">
                    {authorizations?.[purpose]}
                  </span>
                </span>
              </Label>
              {error[name]?.message && (
                <p className="text-destructive pl-6 text-xs">{error[name]?.message}</p>
              )}
            </div>
          )}
        />
      ))}
      <Controller
        control={control}
        name={"channel" as FieldPath<Values>}
        render={({ field }) => (
          <div className="sm:w-64">
            <SelectField
              label="Medio de la autorización"
              value={String(field.value)}
              onChange={field.onChange}
              options={CHANNEL_OPTIONS}
            />
          </div>
        )}
      />
    </fieldset>
  );
}
