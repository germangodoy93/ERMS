import { AlertCircle, CheckCircle2, Plus, Undo2, XCircle } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { SelectField } from "@/components/SelectField";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import { MANUAL_OPTIONS, RESULT_LABELS, RESULT_TONE } from "@/modules/diagnostics/presentation";
import { useParts } from "@/modules/inventory/hooks";
import { errorMessage } from "@/services/errors";
import type { DiagnosticResultCode, RepairOverview, RepairTask, WorkOrder } from "@/types/api";

import { useRepair, useRepairActions } from "../hooks";

export function RepairPanel({ order }: { order: WorkOrder }) {
  const repair = useRepair(order.id);
  if (repair.isPending) return <Skeleton className="h-32" />;
  if (repair.isError)
    return <p className="text-destructive text-sm">{errorMessage(repair.error)}</p>;
  const data = repair.data;
  return (
    <div className="grid gap-5">
      <section className="grid gap-2">
        <h3 className="text-sm font-medium">Trabajos realizados</h3>
        {data.tasks.length === 0 && (
          <p className="text-muted-foreground text-sm">
            {data.can_repair ? "Registre el primer trabajo." : "Sin trabajos registrados."}
          </p>
        )}
        {data.tasks.map((task) => (
          <TaskCard key={task.id} orderId={order.id} task={task} editable={data.can_repair} />
        ))}
        {data.can_repair && <NewTask orderId={order.id} />}
      </section>
      <QualitySection order={order} data={data} />
    </div>
  );
}

function NewTask({ orderId }: { orderId: string }) {
  const actions = useRepairActions(orderId);
  const [description, setDescription] = useState("");
  const [minutes, setMinutes] = useState("");
  const submit = async () => {
    try {
      await actions.addTask.mutateAsync({
        description: description.trim(),
        minutes: minutes ? Number(minutes) : null,
      });
      setDescription("");
      setMinutes("");
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };
  return (
    <div className="grid gap-2 rounded-md border border-dashed p-3">
      <Label htmlFor="task-description">Nuevo trabajo</Label>
      <Textarea
        id="task-description"
        placeholder="Qué se hizo y cómo"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <div className="flex flex-wrap items-center gap-2">
        <Input
          className="w-40"
          inputMode="numeric"
          placeholder="Minutos"
          aria-label="Minutos de trabajo"
          value={minutes}
          onChange={(e) => setMinutes(e.target.value.replace(/\D/g, ""))}
        />
        <Button
          className="ml-auto"
          disabled={description.trim().length < 3 || actions.addTask.isPending}
          onClick={() => void submit()}
        >
          <Plus /> Registrar trabajo
        </Button>
      </div>
    </div>
  );
}

function TaskCard({
  orderId,
  task,
  editable,
}: {
  orderId: string;
  task: RepairTask;
  editable: boolean;
}) {
  const actions = useRepairActions(orderId);
  const parts = useParts({}, editable);
  const [partId, setPartId] = useState("");
  const [quantity, setQuantity] = useState("1");

  const consume = async () => {
    try {
      await actions.consume.mutateAsync({ taskId: task.id, partId, quantity: Number(quantity) });
      setPartId("");
      setQuantity("1");
      toast.success("Repuesto descontado del inventario.");
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };

  return (
    <div className="grid gap-2 rounded-md border p-3 text-sm">
      <p className="whitespace-pre-wrap">{task.description}</p>
      <p className="text-muted-foreground text-xs">
        {task.technician?.full_name ?? "—"} · {formatDateTime(task.created_at)}
        {task.labor_minutes ? ` · ${task.labor_minutes} min` : ""}
      </p>
      {task.parts.length > 0 && (
        <ul className="grid gap-1">
          {task.parts.map((p) => (
            <li key={p.id} className="flex items-center gap-2">
              <span className={cn(p.returned && "text-muted-foreground line-through")}>
                {p.quantity} × {p.sku} · {p.name}
              </span>
              {p.returned && <Badge variant="outline">Devuelto</Badge>}
              {editable && !p.returned && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="ml-auto"
                  onClick={() =>
                    void actions.returnPart
                      .mutateAsync({ taskId: task.id, repairPartId: p.id })
                      .catch((e: unknown) => toast.error(errorMessage(e)))
                  }
                >
                  <Undo2 /> Devolver
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
      {editable && (
        <div className="flex flex-wrap items-end gap-2">
          <div className="min-w-56 flex-1">
            <SelectField
              label="Usar repuesto del inventario"
              value={partId}
              onChange={setPartId}
              placeholder="Seleccione"
              options={(parts.data ?? []).map((p) => ({
                value: p.id,
                label: `${p.sku} · ${p.name} (stock ${p.stock})`,
              }))}
            />
          </div>
          <Input
            className="w-20"
            aria-label="Cantidad"
            inputMode="numeric"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value.replace(/\D/g, ""))}
          />
          <Button
            variant="outline"
            disabled={!partId || !Number(quantity) || actions.consume.isPending}
            onClick={() => void consume()}
          >
            Descontar
          </Button>
        </div>
      )}
    </div>
  );
}

function QualitySection({ order, data }: { order: WorkOrder; data: RepairOverview }) {
  const actions = useRepairActions(order.id);
  const [results, setResults] = useState<Record<string, DiagnosticResultCode>>({});
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const complete = data.qc_tests.every((t) => results[t.test_code]);

  const submit = async () => {
    setError(null);
    try {
      const check = await actions.qualityCheck.mutateAsync({
        results: data.qc_tests.map((t) => ({
          test_code: t.test_code,
          result: results[t.test_code]!,
        })),
        notes: notes.trim() || null,
      });
      setResults({});
      setNotes("");
      toast[check.passed ? "success" : "error"](
        check.passed
          ? "Control de calidad aprobado: ya puede marcar el equipo listo para entrega."
          : "Control de calidad no aprobado: devuelva el equipo a reparación con el motivo.",
      );
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <section className="grid gap-2">
      <h3 className="text-sm font-medium">Control de calidad</h3>
      {data.quality_checks.map((check) => (
        <div key={check.id} className="flex flex-wrap items-center gap-2 text-sm">
          {check.passed ? (
            <CheckCircle2 className="text-success size-4" />
          ) : (
            <XCircle className="text-destructive size-4" />
          )}
          <span>{check.passed ? "Aprobado" : "No aprobado"}</span>
          <span className="text-muted-foreground">
            {formatDateTime(check.checked_at)} · {check.checked_by?.full_name ?? "—"}
          </span>
          {!check.passed && (
            <span className="text-muted-foreground">
              Fallas:{" "}
              {check.results
                .filter((r) => r.result === "FAIL")
                .map((r) => r.name)
                .join(", ")}
            </span>
          )}
        </div>
      ))}
      {data.quality_checks.length === 0 && !data.can_check && (
        <p className="text-muted-foreground text-sm">
          Se registra con la orden en Control de calidad.
        </p>
      )}
      {data.can_check && (
        <div className="grid gap-2 rounded-md border p-3">
          {error && (
            <Alert variant="destructive">
              <AlertCircle />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {data.qc_tests.map((test) => (
            <div key={test.test_code} className="flex flex-wrap items-center gap-2 text-sm">
              <span className="w-44 font-medium">{test.name}</span>
              <div
                role="radiogroup"
                aria-label={`Calidad: ${test.name}`}
                className="flex flex-wrap gap-1"
              >
                {MANUAL_OPTIONS.map((option) => (
                  <button
                    key={option}
                    type="button"
                    role="radio"
                    aria-checked={results[test.test_code] === option}
                    onClick={() => setResults((r) => ({ ...r, [test.test_code]: option }))}
                    className={cn(
                      "rounded-md border px-2 py-0.5 text-xs",
                      results[test.test_code] === option ? RESULT_TONE[option] : "hover:bg-muted",
                    )}
                  >
                    {RESULT_LABELS[option]}
                  </button>
                ))}
              </div>
            </div>
          ))}
          <Textarea
            aria-label="Observaciones del control de calidad"
            placeholder="Observaciones (opcional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
          <div className="flex justify-end">
            <Button
              disabled={!complete || actions.qualityCheck.isPending}
              onClick={() => void submit()}
            >
              Registrar control de calidad
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}
