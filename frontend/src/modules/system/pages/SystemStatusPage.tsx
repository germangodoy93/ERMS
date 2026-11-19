import { AlertTriangle, CheckCircle2, RefreshCw, ServerCrash } from "lucide-react";

import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { ComponentHealth } from "@/types/api";

import { useReadiness } from "../hooks/useReadiness";
import {
  COMPONENT_STATUS_PRESENTATION,
  OVERALL_STATUS_PRESENTATION,
  componentLabel,
  environmentLabel,
  formatBogotaDateTime,
  formatLatency,
} from "../presentation";

export function SystemStatusPage() {
  const { data, isPending, isError, isFetching, refetch } = useReadiness();

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Estado del sistema</h1>
          <p className="text-muted-foreground text-sm">
            Verificación en vivo de la comunicación entre la interfaz, la API y la base de datos.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void refetch()} disabled={isFetching}>
          <RefreshCw className={cn(isFetching && "animate-spin")} />
          Actualizar
        </Button>
      </header>

      {isPending && <LoadingState />}

      {isError && (
        <Card role="alert" className="border-destructive/40">
          <CardHeader className="flex flex-row items-center gap-3">
            <ServerCrash className="text-destructive size-6 shrink-0" />
            <div>
              <CardTitle>No hay conexión con la API</CardTitle>
              <CardDescription>
                El backend no respondió. Verifique que el servicio esté en ejecución.
              </CardDescription>
            </div>
          </CardHeader>
        </Card>
      )}

      {data && (
        <>
          <OverallBanner status={data.status} />
          <section aria-label="Componentes" className="grid gap-4 sm:grid-cols-2">
            {data.components.map((component) => (
              <ComponentCard key={component.name} component={component} />
            ))}
          </section>
          <dl className="text-muted-foreground grid gap-x-8 gap-y-1 text-sm sm:grid-cols-3">
            <MetaItem label="Versión API" value={data.version} />
            <MetaItem label="Entorno" value={environmentLabel(data.environment)} />
            <MetaItem label="Última verificación" value={formatBogotaDateTime(data.checked_at)} />
          </dl>
        </>
      )}
    </div>
  );
}

function OverallBanner({ status }: { status: keyof typeof OVERALL_STATUS_PRESENTATION }) {
  const presentation = OVERALL_STATUS_PRESENTATION[status];
  const ok = presentation.tone === "success";
  const Icon = ok ? CheckCircle2 : AlertTriangle;
  return (
    <Card
      role="status"
      className={cn(ok ? "border-success/40" : "border-destructive/40")}
      data-testid="overall-status"
    >
      <CardHeader className="flex flex-row items-center gap-3">
        <Icon className={cn("size-6 shrink-0", ok ? "text-success" : "text-destructive")} />
        <div>
          <CardTitle>{presentation.title}</CardTitle>
          <CardDescription>{presentation.description}</CardDescription>
        </div>
      </CardHeader>
    </Card>
  );
}

function ComponentCard({ component }: { component: ComponentHealth }) {
  const status = COMPONENT_STATUS_PRESENTATION[component.status];
  const latency = formatLatency(component.latency_ms);
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-2">
        <div className="space-y-1">
          <CardTitle className="text-base">{componentLabel(component.name)}</CardTitle>
          <CardDescription>{component.critical ? "Crítico" : "No crítico"}</CardDescription>
        </div>
        <StatusBadge tone={status.tone} label={status.label} />
      </CardHeader>
      <CardContent className="text-muted-foreground space-y-1 text-sm">
        {component.detail && <p>{component.detail}</p>}
        {latency && <p className="font-mono text-xs">Latencia: {latency}</p>}
      </CardContent>
    </Card>
  );
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs tracking-wide uppercase">{label}</dt>
      <dd className="text-foreground font-mono">{value}</dd>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Cargando estado del sistema">
      <Skeleton className="h-20 w-full" />
      <div className="grid gap-4 sm:grid-cols-2">
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
    </div>
  );
}
