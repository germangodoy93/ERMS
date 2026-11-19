import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, Plus } from "lucide-react";
import { useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";

import { FormField } from "@/components/FormField";
import { SelectField } from "@/components/SelectField";
import { Alert, AlertDescription } from "@/components/ui/alert";
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
import { errorMessage } from "@/services/errors";
import type { Device, DeviceCreate, DeviceUpdate } from "@/types/api";

import {
  useCategories,
  useCreateDevice,
  useCreateModel,
  useManufacturers,
  useModels,
  useUpdateDevice,
} from "../hooks";
import { deviceSchema, type DeviceValues } from "../validation";

function emptyToNull(value: string): string | null {
  return value === "" ? null : value;
}

/** Register a device for a customer, or edit one (device set). */
export function DeviceFormDialog({
  open,
  onOpenChange,
  customerId,
  device,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  customerId: string;
  device?: Device;
}) {
  const categories = useCategories();
  const manufacturers = useManufacturers();
  const createDevice = useCreateDevice();
  const updateDevice = useUpdateDevice();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<DeviceValues>({
    resolver: zodResolver(deviceSchema),
    defaultValues: {
      category_code: device?.model.category.code ?? "",
      manufacturer_id: device?.model.manufacturer.id ?? "",
      model_id: device?.model.id ?? "",
      serial_number: device?.serial_number ?? "",
      imei: device?.imei ?? "",
      operating_system: device?.operating_system ?? "",
      storage: device?.storage ?? "",
      color: device?.color ?? "",
      notes: device?.notes ?? "",
    },
  });

  const category = useWatch({ control, name: "category_code" });
  const manufacturerId = useWatch({ control, name: "manufacturer_id" });
  const models = useModels(
    { manufacturer_id: manufacturerId, category },
    Boolean(category && manufacturerId),
  );

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    const fields = {
      model_id: values.model_id,
      serial_number: emptyToNull(values.serial_number),
      imei: emptyToNull(values.imei),
      operating_system: emptyToNull(values.operating_system),
      storage: emptyToNull(values.storage),
      color: emptyToNull(values.color),
      notes: emptyToNull(values.notes),
    };
    try {
      if (device) {
        const changes: DeviceUpdate = {};
        if (fields.model_id !== device.model.id) changes.model_id = fields.model_id;
        for (const key of [
          "serial_number",
          "imei",
          "operating_system",
          "storage",
          "color",
          "notes",
        ] as const) {
          if (fields[key] !== device[key]) changes[key] = fields[key];
        }
        await updateDevice.mutateAsync({ id: device.id, changes });
        toast.success("Equipo actualizado.");
      } else {
        await createDevice.mutateAsync({ customerId, payload: fields satisfies DeviceCreate });
        toast.success("Equipo registrado.");
      }
      onOpenChange(false);
    } catch (error) {
      setServerError(errorMessage(error));
    }
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92dvh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{device ? "Editar equipo" : "Registrar equipo"}</DialogTitle>
          <DialogDescription>
            No registre contraseñas ni patrones de desbloqueo del equipo.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} className="grid gap-4" noValidate>
          {serverError && (
            <Alert variant="destructive">
              <AlertCircle />
              <AlertDescription>{serverError}</AlertDescription>
            </Alert>
          )}
          <div className="grid gap-4 sm:grid-cols-3">
            <Controller
              control={control}
              name="category_code"
              render={({ field }) => (
                <SelectField
                  label="Categoría"
                  value={field.value}
                  onChange={(v) => {
                    field.onChange(v);
                    setValue("model_id", "");
                  }}
                  options={(categories.data ?? []).map((c) => ({ value: c.code, label: c.name }))}
                  placeholder="Seleccione"
                  error={errors.category_code?.message}
                />
              )}
            />
            <Controller
              control={control}
              name="manufacturer_id"
              render={({ field }) => (
                <SelectField
                  label="Fabricante"
                  value={field.value}
                  onChange={(v) => {
                    field.onChange(v);
                    setValue("model_id", "");
                  }}
                  options={(manufacturers.data ?? []).map((m) => ({ value: m.id, label: m.name }))}
                  placeholder="Seleccione"
                  error={errors.manufacturer_id?.message}
                />
              )}
            />
            <Controller
              control={control}
              name="model_id"
              render={({ field }) => (
                <SelectField
                  label="Modelo"
                  value={field.value}
                  onChange={field.onChange}
                  options={(models.data ?? []).map((m) => ({ value: m.id, label: m.name }))}
                  placeholder={
                    category && manufacturerId
                      ? models.data?.length
                        ? "Seleccione"
                        : "Sin modelos: créelo abajo"
                      : "Elija categoría y fabricante"
                  }
                  disabled={!category || !manufacturerId}
                  error={errors.model_id?.message}
                />
              )}
            />
          </div>
          {category && manufacturerId && (
            <NewModelInline
              categoryCode={category}
              manufacturerId={manufacturerId}
              onCreated={(id) => setValue("model_id", id, { shouldValidate: true })}
            />
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              label="IMEI (celulares y tablets)"
              inputMode="numeric"
              autoComplete="off"
              hint="Se obtiene marcando *#06#."
              error={errors.imei?.message}
              {...register("imei")}
            />
            <FormField
              label="Serial"
              autoComplete="off"
              error={errors.serial_number?.message}
              {...register("serial_number")}
            />
            <FormField
              label="Sistema operativo"
              placeholder="Android 15, Windows 11…"
              error={errors.operating_system?.message}
              {...register("operating_system")}
            />
            <div className="grid grid-cols-2 gap-4">
              <FormField
                label="Capacidad"
                placeholder="256 GB"
                error={errors.storage?.message}
                {...register("storage")}
              />
              <FormField label="Color" error={errors.color?.message} {...register("color")} />
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="device-notes">Notas (opcional)</Label>
            <Textarea
              id="device-notes"
              placeholder="Accesorios, marcas visibles… sin contraseñas ni datos personales."
              {...register("notes")}
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Guardando…" : device ? "Guardar cambios" : "Registrar equipo"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function NewModelInline({
  categoryCode,
  manufacturerId,
  onCreated,
}: {
  categoryCode: string;
  manufacturerId: string;
  onCreated: (modelId: string) => void;
}) {
  const createModel = useCreateModel();
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setError(null);
    try {
      const model = await createModel.mutateAsync({
        manufacturer_id: manufacturerId,
        category_code: categoryCode,
        name: name.trim(),
      });
      setName("");
      onCreated(model.id);
      toast.success(`Modelo ${model.name} creado.`);
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <div className="grid gap-1.5">
      <Label htmlFor="new-model">¿El modelo no está en la lista?</Label>
      <div className="flex gap-2">
        <Input
          id="new-model"
          placeholder="Nombre del modelo, p. ej. Galaxy A55"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              if (name.trim()) void submit();
            }
          }}
        />
        <Button
          type="button"
          variant="outline"
          disabled={!name.trim() || createModel.isPending}
          onClick={() => void submit()}
        >
          <Plus /> Crear
        </Button>
      </div>
      {error && <p className="text-destructive text-xs">{error}</p>}
    </div>
  );
}
