import { AlertTriangle, Clock, PackageCheck, ShieldCheck, Timer, Wallet } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { PendingNoticesCard } from "@/modules/notices/components/PendingNoticesCard";
import { WorkOrderStatusBadge } from "@/modules/workorders/components/WorkOrderStatusBadge";
import { formatMoney, PAYMENT_LABELS } from "@/modules/workorders/presentation";
import { errorMessage } from "@/services/errors";
import { useAuthStore } from "@/stores/auth";

import { useDashboard } from "../hooks";

function Kpi({
  label,
  value,
  hint,
  icon,
  tone = "default",
  to,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  icon: ReactNode;
  tone?: "default" | "warning" | "danger";
  to?: string;
}) {
  const body = (
    <Card className={cn("h-full", to && "hover:bg-muted/40 transition-colors")}>
      <CardContent className="flex items-start gap-3 p-4">
        <div
          className={cn(
            "rounded-md p-2",
            tone === "danger" && "bg-destructive/10 text-destructive",
            tone === "warning" && "bg-warning/20",
            tone === "default" && "bg-muted",
          )}
        >
          {icon}
        </div>
        <div>
          <p className="text-muted-foreground text-xs">{label}</p>
          <p className="text-2xl font-semibold">{value}</p>
          {hint && <p className="text-muted-foreground text-xs">{hint}</p>}
        </div>
      </CardContent>
    </Card>
  );
  return to ? <Link to={to}>{body}</Link> : body;
}

export function DashboardPage() {
  const dashboard = useDashboard();
  const name = useAuthStore((s) => s.user?.full_name.split(" ")[0]);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Hola, {name}</h1>
        <p className="text-muted-foreground text-sm">
          {dashboard.data?.scope === "MINE"
            ? "Tus órdenes asignadas."
            : "Resumen del taller en tiempo real."}
        </p>
      </header>
      {dashboard.isPending && <Skeleton className="h-64" />}
      {dashboard.isError && (
        <Alert variant="destructive">
          <AlertTriangle />
          <AlertDescription>{errorMessage(dashboard.error)}</AlertDescription>
        </Alert>
      )}
      {dashboard.data && <DashboardBody data={dashboard.data} />}
    </div>
  );
}

function DashboardBody({ data }: { data: NonNullable<ReturnType<typeof useDashboard>["data"]> }) {
  const workshop = data.scope === "WORKSHOP";
  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi
          label="Recibidas hoy"
          value={data.received_today}
          hint={`${data.received_week} esta semana`}
          icon={<Clock className="size-4" />}
        />
        <Kpi
          label="Atrasadas"
          value={data.overdue}
          hint="Trabajo pendiente con fecha estimada vencida"
          icon={<AlertTriangle className="size-4" />}
          tone={data.overdue ? "danger" : "default"}
          to="/ordenes"
        />
        <Kpi
          label="Esperando al cliente"
          value={data.awaiting_customer}
          hint={data.expired_quotes ? `${data.expired_quotes} cotizaciones vencidas` : undefined}
          icon={<Timer className="size-4" />}
          tone={data.expired_quotes ? "warning" : "default"}
          to="/ordenes"
        />
        <Kpi
          label="Listas para entrega"
          value={data.ready_for_delivery}
          hint={
            data.ready_balance && Number(data.ready_balance) > 0
              ? `Saldo por cobrar ${formatMoney(data.ready_balance)}`
              : undefined
          }
          icon={<PackageCheck className="size-4" />}
          to="/ordenes"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <PendingNoticesCard />
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Órdenes abiertas por estado</CardTitle>
          </CardHeader>
          <CardContent>
            {data.open_by_status.length === 0 ? (
              <p className="text-muted-foreground text-sm">No hay órdenes abiertas.</p>
            ) : (
              <ul className="grid gap-2">
                {data.open_by_status.map((s) => (
                  <li key={s.status} className="flex items-center justify-between">
                    <WorkOrderStatusBadge status={s.status} />
                    <span className="font-medium">{s.count}</span>
                  </li>
                ))}
              </ul>
            )}
            {data.avg_turnaround_days !== null && (
              <p className="text-muted-foreground mt-4 text-sm">
                Tiempo promedio de recepción a entrega (90 días):{" "}
                <span className="text-foreground font-medium">
                  {data.avg_turnaround_days.toLocaleString("es-CO")} días
                </span>
              </p>
            )}
          </CardContent>
        </Card>

        {workshop && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Wallet className="size-4" /> Ingresos del mes
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold">{formatMoney(data.income_month_total)}</p>
              <ul className="mt-3 grid gap-1 text-sm">
                {data.income_month?.map((m) => (
                  <li key={m.method} className="flex justify-between">
                    <span className="text-muted-foreground">{PAYMENT_LABELS[m.method]}</span>
                    <span>{formatMoney(m.amount)}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {workshop && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Carga por técnico</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="grid gap-1 text-sm">
                {data.technician_load?.length === 0 && (
                  <li className="text-muted-foreground">Sin órdenes abiertas.</li>
                )}
                {data.technician_load?.map((t) => (
                  <li key={t.technician?.id ?? "none"} className="flex justify-between">
                    <span>{t.technician?.full_name ?? "Sin asignar"}</span>
                    <span className="font-medium">{t.open_orders}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {workshop && (
          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
            <Kpi
              label="Repuestos con stock bajo"
              value={data.low_stock ?? 0}
              icon={<AlertTriangle className="size-4" />}
              tone={data.low_stock ? "warning" : "default"}
              to="/inventario"
            />
            <Kpi
              label="Garantías que vencen en 15 días"
              value={data.warranties_expiring ?? 0}
              icon={<ShieldCheck className="size-4" />}
            />
            <Kpi
              label="Reclamos de garantía abiertos"
              value={data.open_claims ?? 0}
              icon={<ShieldCheck className="size-4" />}
              tone={data.open_claims ? "warning" : "default"}
            />
          </div>
        )}
      </div>
    </>
  );
}
