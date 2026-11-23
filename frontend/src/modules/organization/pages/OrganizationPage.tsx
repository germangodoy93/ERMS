import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, AlertTriangle, CheckCircle2, FileText } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { FormField } from "@/components/FormField";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { formatDateTime } from "@/lib/format";
import { errorMessage } from "@/services/errors";
import type { Organization, OrganizationUpdate } from "@/types/api";

import { ReceptionTermsCard } from "../components/ReceptionTermsCard";
import {
  useCurrentPolicy,
  useOrganization,
  usePolicyDraft,
  usePublishPolicy,
  useUpdateOrganization,
} from "../hooks";
import { organizationSchema, POLICY_MIN_LENGTH, type OrganizationValues } from "../schemas";

export function OrganizationPage() {
  const organization = useOrganization();

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Datos del taller</h1>
        <p className="text-muted-foreground text-sm">
          Identifican al responsable del tratamiento de datos (Ley 1581 de 2012) y aparecen en la
          política y en las autorizaciones de los clientes.
        </p>
      </header>
      {organization.isPending && <Skeleton className="h-80" />}
      {organization.isError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{errorMessage(organization.error)}</AlertDescription>
        </Alert>
      )}
      {organization.data && (
        <>
          <OrganizationForm key={organization.data.id} organization={organization.data} />
          <PolicyCard />
          <ReceptionTermsCard />
        </>
      )}
    </div>
  );
}

function OrganizationForm({ organization }: { organization: Organization }) {
  const update = useUpdateOrganization();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<OrganizationValues>({
    resolver: zodResolver(organizationSchema),
    defaultValues: {
      name: organization.name,
      legal_name: organization.legal_name ?? "",
      tax_id: organization.tax_id ?? "",
      address: organization.address ?? "",
      city: organization.city ?? "",
      phone: organization.phone ?? "",
      email: organization.email ?? "",
      warranty_days: String(organization.warranty_days),
      assembly_bottleneck_gap: String(organization.assembly_bottleneck_gap),
      assembly_min_ram_gb: String(organization.assembly_min_ram_gb),
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    const payload: OrganizationUpdate = {
      name: values.name,
      legal_name: values.legal_name || null,
      tax_id: values.tax_id || null,
      address: values.address || null,
      city: values.city || null,
      phone: values.phone || null,
      email: values.email || null,
      warranty_days: Number(values.warranty_days),
      assembly_bottleneck_gap: Number(values.assembly_bottleneck_gap),
      assembly_min_ram_gb: Number(values.assembly_min_ram_gb),
    };
    try {
      const saved = await update.mutateAsync(payload);
      reset({
        name: saved.name,
        legal_name: saved.legal_name ?? "",
        tax_id: saved.tax_id ?? "",
        address: saved.address ?? "",
        city: saved.city ?? "",
        phone: saved.phone ?? "",
        email: saved.email ?? "",
        warranty_days: String(saved.warranty_days),
        assembly_bottleneck_gap: String(saved.assembly_bottleneck_gap),
        assembly_min_ram_gb: String(saved.assembly_min_ram_gb),
      });
      toast.success("Datos del taller guardados.");
    } catch (error) {
      setServerError(errorMessage(error));
    }
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Responsable del tratamiento</CardTitle>
        <CardDescription>
          Todos los campos son necesarios para publicar la política de datos.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="grid gap-4" noValidate>
          {serverError && (
            <Alert variant="destructive">
              <AlertCircle />
              <AlertDescription>{serverError}</AlertDescription>
            </Alert>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              label="Nombre del taller"
              error={errors.name?.message}
              {...register("name")}
            />
            <FormField
              label="Razón social"
              hint="Como aparece en el RUT."
              error={errors.legal_name?.message}
              {...register("legal_name")}
            />
            <FormField
              label="NIT"
              placeholder="900123456-7"
              hint="El dígito de verificación se calcula si no lo escribe."
              error={errors.tax_id?.message}
              {...register("tax_id")}
            />
            <FormField label="Ciudad" error={errors.city?.message} {...register("city")} />
            <FormField label="Dirección" error={errors.address?.message} {...register("address")} />
            <FormField
              label="Teléfono"
              type="tel"
              error={errors.phone?.message}
              {...register("phone")}
            />
            <FormField
              label="Días de garantía por defecto"
              inputMode="numeric"
              hint="Se aplica al entregar un equipo reparado; se puede ajustar en cada entrega."
              error={errors.warranty_days?.message}
              {...register("warranty_days")}
            />
            <FormField
              label="Ensamble: diferencia para avisar cuello de botella"
              inputMode="numeric"
              hint="Puntos de diferencia entre el índice del procesador y el de la gráfica."
              error={errors.assembly_bottleneck_gap?.message}
              {...register("assembly_bottleneck_gap")}
            />
            <FormField
              label="Ensamble: RAM mínima para diseño y gaming (GB)"
              inputMode="numeric"
              error={errors.assembly_min_ram_gb?.message}
              {...register("assembly_min_ram_gb")}
            />
            <FormField
              label="Correo para consultas y reclamos"
              type="email"
              error={errors.email?.message}
              {...register("email")}
            />
          </div>
          <div className="flex justify-end">
            <Button type="submit" disabled={isSubmitting || !isDirty}>
              {isSubmitting ? "Guardando…" : "Guardar datos"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function PolicyCard() {
  const current = useCurrentPolicy();
  const [editing, setEditing] = useState(false);
  const policy = current.data?.policy;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Política de tratamiento de datos</CardTitle>
        <CardDescription>
          Cada autorización de un cliente queda ligada a la versión que estaba vigente.
        </CardDescription>
        {!editing && (
          <CardAction>
            <Button variant="outline" onClick={() => setEditing(true)} disabled={current.isPending}>
              <FileText /> {policy ? "Publicar nueva versión" : "Revisar y publicar"}
            </Button>
          </CardAction>
        )}
      </CardHeader>
      <CardContent className="grid gap-4">
        {current.isPending && <Skeleton className="h-16" />}
        {current.data &&
          (policy ? (
            <Alert>
              <CheckCircle2 className="text-success" />
              <AlertTitle>Versión {policy.version} vigente</AlertTitle>
              <AlertDescription>
                Publicada el {formatDateTime(policy.published_at)}.
              </AlertDescription>
            </Alert>
          ) : (
            <Alert variant="destructive">
              <AlertTriangle />
              <AlertTitle>Sin política publicada</AlertTitle>
              <AlertDescription>
                Mientras no se publique, no se pueden registrar clientes.
              </AlertDescription>
            </Alert>
          ))}
        {editing && (
          <PolicyEditor currentContent={policy?.content} onDone={() => setEditing(false)} />
        )}
        {!editing && policy && (
          <details className="rounded-md border p-3 text-sm">
            <summary className="cursor-pointer font-medium">Ver texto vigente</summary>
            <p className="mt-3 whitespace-pre-wrap">{policy.content}</p>
          </details>
        )}
      </CardContent>
    </Card>
  );
}

function PolicyEditor({
  currentContent,
  onDone,
}: {
  currentContent: string | undefined;
  onDone: () => void;
}) {
  const draft = usePolicyDraft(true);
  const publish = usePublishPolicy();
  const [content, setContent] = useState<string | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  if (draft.isPending) return <Skeleton className="h-64" />;
  if (draft.isError) {
    return <p className="text-destructive text-sm">{errorMessage(draft.error)}</p>;
  }

  const text = content ?? currentContent ?? draft.data.content;
  const missing = draft.data.missing_fields;
  const tooShort = text.trim().length < POLICY_MIN_LENGTH;

  const onPublish = async () => {
    setServerError(null);
    try {
      const published = await publish.mutateAsync(text);
      toast.success(`Política versión ${published.version} publicada.`);
      onDone();
    } catch (error) {
      setServerError(errorMessage(error));
    }
  };

  return (
    <div className="grid gap-3">
      <Alert>
        <AlertTriangle />
        <AlertTitle>Texto base, no es asesoría legal</AlertTitle>
        <AlertDescription>
          La plantilla incluye los elementos mínimos de la Ley 1581 de 2012 y el Decreto 1377 de
          2013. Revísela y ajústela a su taller; lo ideal es que la revise un abogado.
        </AlertDescription>
      </Alert>
      {missing.length > 0 && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>
            Complete y guarde los datos del taller antes de publicar: {missing.join(", ")}.
          </AlertDescription>
        </Alert>
      )}
      {serverError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{serverError}</AlertDescription>
        </Alert>
      )}
      <div className="flex justify-end">
        <Button variant="ghost" size="sm" onClick={() => setContent(draft.data.content)}>
          Restablecer plantilla
        </Button>
      </div>
      <Textarea
        aria-label="Texto de la política"
        className="max-h-[32rem] min-h-80 font-mono text-xs"
        value={text}
        onChange={(e) => setContent(e.target.value)}
      />
      <Label className="flex items-center gap-2 font-normal">
        <Checkbox checked={reviewed} onCheckedChange={(v) => setReviewed(v === true)} />
        Revisé el texto y los datos del responsable.
      </Label>
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onDone}>
          Cancelar
        </Button>
        <Button
          onClick={() => void onPublish()}
          disabled={!reviewed || tooShort || missing.length > 0 || publish.isPending}
        >
          {publish.isPending ? "Publicando…" : "Publicar"}
        </Button>
      </div>
    </div>
  );
}
