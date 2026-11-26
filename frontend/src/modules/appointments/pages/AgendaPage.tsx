import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  MapPin,
  MonitorSmartphone,
  Plus,
} from "lucide-react";
import { useMemo, useState } from "react";

import { SelectField } from "@/components/SelectField";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { PERMS, useCan } from "@/modules/auth/permissions";
import { todayInBogota } from "@/modules/workorders/presentation";
import { errorMessage } from "@/services/errors";
import type { AgendaOptions, AppointmentRead, Holiday } from "@/types/api";

import { AppointmentDetailDialog } from "../components/AppointmentDetailDialog";
import { AppointmentFormDialog } from "../components/AppointmentFormDialog";
import { FieldServicesCard, ServiceHoursCard } from "../components/AgendaSettings";
import { useAgendaOptions, useAppointments, useHolidays } from "../hooks";
import {
  addDays,
  bogotaDate,
  formatDayTitle,
  groupByDay,
  hoursLabel,
  MODALITY_LABELS,
  timeRange,
  weekdayOf,
  weekStart,
} from "../presentation";

type View = "week" | "day";

export function AgendaPage() {
  const options = useAgendaOptions();
  const canConfigure = useCan(PERMS.ORGANIZATION_MANAGE);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Agenda</h1>
        <p className="text-muted-foreground text-sm">
          Citas de atención remota y visitas en sitio.
        </p>
      </header>
      {options.isPending && <Skeleton className="h-96" />}
      {options.isError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{errorMessage(options.error)}</AlertDescription>
        </Alert>
      )}
      {options.data &&
        (canConfigure ? (
          <Tabs defaultValue="agenda">
            <TabsList>
              <TabsTrigger value="agenda">Citas</TabsTrigger>
              <TabsTrigger value="settings">Servicios y horario</TabsTrigger>
            </TabsList>
            <TabsContent value="agenda" className="mt-4">
              <Agenda options={options.data} />
            </TabsContent>
            <TabsContent value="settings" className="mt-4 grid gap-6">
              <FieldServicesCard />
              <ServiceHoursCard />
            </TabsContent>
          </Tabs>
        ) : (
          <Agenda options={options.data} />
        ))}
    </div>
  );
}

function Agenda({ options }: { options: AgendaOptions }) {
  const today = todayInBogota();
  const [view, setView] = useState<View>("week");
  const [anchor, setAnchor] = useState(today);
  const [technicianId, setTechnicianId] = useState("");
  const [includeCancelled, setIncludeCancelled] = useState(false);
  const [selected, setSelected] = useState<AppointmentRead | null>(null);
  const [form, setForm] = useState<{ appointment?: AppointmentRead; date?: string } | null>(null);

  const days = useMemo(() => {
    if (view === "day") return [anchor];
    const start = weekStart(anchor);
    return Array.from({ length: 7 }, (_, i) => addDays(start, i));
  }, [view, anchor]);
  const from = days[0] ?? anchor;
  const to = days[days.length - 1] ?? anchor;
  const appointments = useAppointments({ from, to, technicianId, includeCancelled });
  const holidays = useHolidays(from, to);
  const holidayOf = (day: string) => holidays.data?.find((h: Holiday) => h.date === day);
  const groups = groupByDay(appointments.data ?? [], days);
  // Sunday is shown only when it has service hours or appointments.
  const visibleDays = days.filter(
    (d) =>
      view === "day" ||
      weekdayOf(d) < 6 ||
      options.hours[6]?.opens ||
      (groups.get(d)?.length ?? 0) > 0,
  );
  const step = view === "week" ? 7 : 1;

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon"
            aria-label="Anterior"
            onClick={() => setAnchor(addDays(anchor, -step))}
          >
            <ChevronLeft />
          </Button>
          <Button variant="outline" onClick={() => setAnchor(today)}>
            Hoy
          </Button>
          <Button
            variant="outline"
            size="icon"
            aria-label="Siguiente"
            onClick={() => setAnchor(addDays(anchor, step))}
          >
            <ChevronRight />
          </Button>
        </div>
        <div className="flex rounded-md border p-0.5">
          {(["week", "day"] as const).map((v) => (
            <Button
              key={v}
              size="sm"
              variant={view === v ? "secondary" : "ghost"}
              onClick={() => setView(v)}
            >
              {v === "week" ? "Semana" : "Día"}
            </Button>
          ))}
        </div>
        <p className="text-sm font-medium">
          {view === "week"
            ? `${formatDayTitle(from)} – ${formatDayTitle(to)}`
            : formatDayTitle(anchor)}
        </p>
        <div className="ml-auto flex flex-wrap items-end gap-3">
          {options.can_manage && (
            <div className="w-56">
              <SelectField
                label="Técnico"
                value={technicianId}
                onChange={setTechnicianId}
                emptyLabel="Todos"
                options={options.technicians.map((t) => ({ value: t.id, label: t.full_name }))}
              />
            </div>
          )}
          <Label className="flex h-9 items-center gap-2 text-sm font-normal">
            <Checkbox
              checked={includeCancelled}
              onCheckedChange={(v) => setIncludeCancelled(v === true)}
            />
            Ver canceladas
          </Label>
          {options.can_manage && (
            <Button onClick={() => setForm({ date: view === "day" ? anchor : undefined })}>
              <Plus /> Nueva cita
            </Button>
          )}
        </div>
      </div>

      {appointments.isError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{errorMessage(appointments.error)}</AlertDescription>
        </Alert>
      )}

      <div className={cn("grid gap-3", view === "week" && "md:grid-cols-2 xl:grid-cols-3")}>
        {visibleDays.map((day) => {
          const holiday = holidayOf(day);
          const items = groups.get(day) ?? [];
          const hours = options.hours[weekdayOf(day)];
          return (
            <Card key={day} className={cn("gap-3 py-4", day === today && "border-primary")}>
              <CardHeader className="px-4">
                <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-base">
                  <button
                    type="button"
                    className="hover:underline"
                    onClick={() => {
                      setAnchor(day);
                      setView("day");
                    }}
                  >
                    {formatDayTitle(day)}
                  </button>
                  <span className="text-muted-foreground text-xs font-normal">
                    {holiday ? (
                      <Badge variant="secondary">Festivo: {holiday.name}</Badge>
                    ) : (
                      hoursLabel(hours)
                    )}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="grid gap-2 px-4">
                {appointments.isPending && <Skeleton className="h-12" />}
                {!appointments.isPending && items.length === 0 && (
                  <p className="text-muted-foreground text-sm">Sin citas.</p>
                )}
                {items.map((a) => (
                  <AppointmentItem key={a.id} appointment={a} onOpen={() => setSelected(a)} />
                ))}
              </CardContent>
            </Card>
          );
        })}
      </div>

      <AppointmentDetailDialog
        appointment={selected}
        canManage={options.can_manage}
        onClose={() => setSelected(null)}
        onEdit={(a) => {
          setSelected(null);
          setForm({ appointment: a });
        }}
      />
      <AppointmentFormDialog
        options={options}
        open={form !== null}
        onOpenChange={(open) => !open && setForm(null)}
        appointment={form?.appointment}
        initialDate={form?.date}
        onSaved={(a) => setAnchor(bogotaDate(a.starts_at))}
      />
    </div>
  );
}

function AppointmentItem({
  appointment: a,
  onOpen,
}: {
  appointment: AppointmentRead;
  onOpen: () => void;
}) {
  const cancelled = a.status === "CANCELLED";
  return (
    <button
      type="button"
      onClick={onOpen}
      className={cn(
        "hover:bg-muted/60 grid gap-0.5 rounded-md border p-2 text-left text-sm",
        cancelled && "opacity-60",
      )}
    >
      <span className="flex items-center justify-between gap-2">
        <span className={cn("font-medium", cancelled && "line-through")}>{timeRange(a)}</span>
        <span className="text-muted-foreground flex items-center gap-1 text-xs">
          {a.modality === "REMOTE" ? (
            <MonitorSmartphone className="size-3.5" />
          ) : (
            <MapPin className="size-3.5" />
          )}
          {a.modality === "ON_SITE" && a.locality ? a.locality : MODALITY_LABELS[a.modality]}
        </span>
      </span>
      <span>{a.customer.full_name}</span>
      <span className="text-muted-foreground text-xs">
        {a.number} · {a.service.name} · {a.technician?.full_name ?? "Sin asignar"}
        {cancelled ? " · Cancelada" : ""}
      </span>
      {a.overlap_reason && !cancelled && (
        <span className="text-xs font-medium text-amber-700 dark:text-amber-400">
          Cruce autorizado con otra cita
        </span>
      )}
    </button>
  );
}
