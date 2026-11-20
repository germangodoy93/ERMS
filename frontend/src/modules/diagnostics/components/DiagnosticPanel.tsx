import { AlertCircle, Bot, FileDown, Lock, LockOpen, Save } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { saveBlob } from "@/lib/download";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import { PERMS, useCan } from "@/modules/auth/permissions";
import { errorMessage } from "@/services/errors";
import type {
  Diagnostic,
  DiagnosticResultCode,
  DiagnosticResultInput,
  DiagnosticTestResult,
  WorkOrder,
} from "@/types/api";

import { downloadDiagnosticReport } from "../api";
import {
  useCloseDiagnostic,
  useCreatePairing,
  useDiagnostic,
  useReopenDiagnostic,
  useSaveResults,
} from "../hooks";
import {
  countResults,
  MANUAL_OPTIONS,
  pendingManualTests,
  RESULT_LABELS,
  RESULT_TONE,
} from "../presentation";
import { AgentDialog } from "./AgentDialog";

type Draft = Record<string, { result: DiagnosticResultCode | null; observation: string }>;

function initialDraft(diagnostic: Diagnostic): Draft {
  return Object.fromEntries(
    diagnostic.results
      .filter((r) => !r.automated)
      .map((r) => [r.test_code, { result: r.result, observation: r.observation ?? "" }]),
  );
}

export function DiagnosticPanel({ order }: { order: WorkOrder }) {
  const diagnostic = useDiagnostic(order.id);
  if (diagnostic.isPending) return <Skeleton className="h-64" />;
  if (diagnostic.isError) {
    return <p className="text-destructive text-sm">{errorMessage(diagnostic.error)}</p>;
  }
  // Remount the editor when the server data changes (save, agent report, close).
  const version = `${diagnostic.data.state}-${diagnostic.data.agent_reported_at}-${diagnostic.data.results
    .map((r) => r.recorded_at)
    .join()}`;
  return <DiagnosticEditor key={version} order={order} diagnostic={diagnostic.data} />;
}

function DiagnosticEditor({ order, diagnostic }: { order: WorkOrder; diagnostic: Diagnostic }) {
  const [draft, setDraft] = useState<Draft>(() => initialDraft(diagnostic));
  const [conclusion, setConclusion] = useState(diagnostic.conclusion ?? "");
  const [recommendation, setRecommendation] = useState(diagnostic.recommendation ?? "");
  const [error, setError] = useState<string | null>(null);
  const [agentOpen, setAgentOpen] = useState(false);
  const [agentStartedAt, setAgentStartedAt] = useState<string | null>(null);
  const save = useSaveResults(order.id);
  const close = useCloseDiagnostic(order.id);
  const reopen = useReopenDiagnostic(order.id);
  const pairing = useCreatePairing(order.id);
  const canProgress = useCan(PERMS.WORK_ORDERS_PROGRESS);
  const editable = diagnostic.editable;
  const closed = diagnostic.state === "CLOSED";

  const changed: DiagnosticResultInput[] = diagnostic.results
    .filter((r) => !r.automated)
    .flatMap((r) => {
      const d = draft[r.test_code];
      if (!d?.result) return [];
      if (d.result === r.result && d.observation === (r.observation ?? "")) return [];
      return [{ test_code: r.test_code, result: d.result, observation: d.observation || null }];
    });
  const pendingAfterSave = diagnostic.results.filter(
    (r) => !r.automated && !draft[r.test_code]?.result,
  );

  const run = async (action: () => Promise<unknown>, success: string) => {
    setError(null);
    try {
      await action();
      toast.success(success);
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  const onSave = () => run(() => save.mutateAsync(changed), "Resultados guardados.");
  const onClose = () =>
    run(async () => {
      if (changed.length) await save.mutateAsync(changed);
      await close.mutateAsync({
        conclusion: conclusion.trim(),
        recommendation: recommendation.trim() || null,
      });
    }, "Diagnóstico cerrado.");
  const markPendingNotTested = () =>
    setDraft((current) => {
      const next = { ...current };
      for (const r of pendingAfterSave) {
        next[r.test_code] = {
          result: "NOT_TESTED",
          observation: next[r.test_code]?.observation ?? "",
        };
      }
      return next;
    });
  const startAgent = () => {
    setAgentStartedAt(diagnostic.agent_reported_at);
    setAgentOpen(true);
    pairing.mutate();
  };
  const downloadReport = async () => {
    try {
      saveBlob(await downloadDiagnosticReport(order.id), `diagnostico-${order.number}.pdf`);
    } catch (e) {
      toast.error(errorMessage(e, "No se pudo descargar el informe."));
    }
  };

  const counts = countResults(diagnostic);
  const manual = diagnostic.results.filter((r) => !r.automated);
  const automated = diagnostic.results.filter((r) => r.automated);

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <Badge variant="outline">
          {closed ? "Cerrado" : diagnostic.state === "OPEN" ? "En curso" : "Sin iniciar"}
        </Badge>
        <span className="text-muted-foreground">
          {counts.ok} bien · {counts.warning} advertencias · {counts.fail} fallas
          {counts.pending ? ` · ${counts.pending} pendientes` : ""}
        </span>
        <div className="ml-auto flex flex-wrap gap-2">
          {editable && diagnostic.agent_available && (
            <Button variant="outline" size="sm" onClick={startAgent}>
              <Bot /> Diagnóstico con agente
            </Button>
          )}
          {diagnostic.state !== "NOT_STARTED" && (
            <Button variant="outline" size="sm" onClick={() => void downloadReport()}>
              <FileDown /> Informe PDF
            </Button>
          )}
          {closed && order.status === "DIAGNOSTICO" && canProgress && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => void run(() => reopen.mutateAsync(), "Diagnóstico reabierto.")}
            >
              <LockOpen /> Reabrir
            </Button>
          )}
        </div>
      </div>

      {!editable && !closed && order.status !== "DIAGNOSTICO" && (
        <p className="text-muted-foreground text-sm">
          El diagnóstico se registra con la orden en estado Diagnóstico.
        </p>
      )}
      {editable &&
        !diagnostic.agent_available &&
        diagnostic.agent_unavailable_reason &&
        automated.length > 0 && (
          <p className="text-muted-foreground text-sm">
            Agente: {diagnostic.agent_unavailable_reason}
          </p>
        )}
      {error && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <section className="grid gap-2">
        <h3 className="text-sm font-medium">Revisión manual y visual</h3>
        <ul className="divide-y rounded-md border">
          {manual.map((test) => (
            <ManualRow
              key={test.test_code}
              test={test}
              value={draft[test.test_code]}
              editable={editable}
              onChange={(value) => setDraft((d) => ({ ...d, [test.test_code]: value }))}
            />
          ))}
        </ul>
      </section>

      {automated.length > 0 && (
        <section className="grid gap-2">
          <h3 className="flex items-center gap-2 text-sm font-medium">
            <Bot className="size-4" /> Agente de diagnóstico (automático)
            {diagnostic.agent_reported_at && (
              <span className="text-muted-foreground font-normal">
                · {formatDateTime(diagnostic.agent_reported_at)} · v{diagnostic.agent_version}
                {diagnostic.agent_elevated ? " · administrador" : ""}
              </span>
            )}
          </h3>
          <ul className="divide-y rounded-md border">
            {automated.map((test) => (
              <li key={test.test_code} className="flex flex-wrap items-start gap-3 p-3 text-sm">
                <span className="w-44 font-medium">{test.name}</span>
                <ResultBadge result={test.result} />
                <span className="text-muted-foreground min-w-0 flex-1">
                  {test.observation ?? "Sin datos: ejecute el agente."}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {editable && (
        <div className="flex flex-wrap justify-end gap-2">
          {pendingAfterSave.length > 0 && (
            <Button variant="ghost" onClick={markPendingNotTested}>
              Marcar pendientes como "No probado"
            </Button>
          )}
          <Button
            variant="outline"
            disabled={!changed.length || save.isPending}
            onClick={() => void onSave()}
          >
            <Save /> Guardar resultados
          </Button>
        </div>
      )}

      {(editable || closed) && (
        <section className="grid gap-3 rounded-md border p-4">
          <div className="grid gap-1.5">
            <Label htmlFor="diagnostic-conclusion">Conclusión del técnico</Label>
            <Textarea
              id="diagnostic-conclusion"
              value={conclusion}
              disabled={!editable}
              onChange={(e) => setConclusion(e.target.value)}
              placeholder="Causa de la falla y estado general del equipo."
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="diagnostic-recommendation">Reparación recomendada (opcional)</Label>
            <Textarea
              id="diagnostic-recommendation"
              value={recommendation}
              disabled={!editable}
              onChange={(e) => setRecommendation(e.target.value)}
            />
          </div>
          {closed ? (
            <p className="text-muted-foreground flex items-center gap-1 text-sm">
              <Lock className="size-3.5" /> Cerrado el {formatDateTime(diagnostic.closed_at)} por{" "}
              {diagnostic.closed_by?.full_name ?? "—"}.
            </p>
          ) : (
            <div className="flex justify-end">
              <Button
                disabled={
                  conclusion.trim().length < 5 || pendingAfterSave.length > 0 || close.isPending
                }
                title={
                  pendingAfterSave.length
                    ? `Faltan: ${pendingManualTests(diagnostic).join(", ")}`
                    : undefined
                }
                onClick={() => void onClose()}
              >
                <Lock /> Cerrar diagnóstico
              </Button>
            </div>
          )}
        </section>
      )}

      {agentOpen && (
        <AgentDialog
          orderId={order.id}
          pairing={pairing.data}
          error={pairing.error}
          startedAt={agentStartedAt}
          onClose={() => setAgentOpen(false)}
        />
      )}
    </div>
  );
}

function ResultBadge({ result }: { result: DiagnosticResultCode | null }) {
  if (!result) return <Badge variant="outline">Pendiente</Badge>;
  return (
    <Badge variant="outline" className={cn("whitespace-nowrap", RESULT_TONE[result])}>
      {RESULT_LABELS[result]}
    </Badge>
  );
}

function ManualRow({
  test,
  value,
  editable,
  onChange,
}: {
  test: DiagnosticTestResult;
  value: Draft[string] | undefined;
  editable: boolean;
  onChange: (value: Draft[string]) => void;
}) {
  const current = value ?? { result: null, observation: "" };
  if (!editable) {
    return (
      <li className="flex flex-wrap items-start gap-3 p-3 text-sm">
        <span className="w-44 font-medium">{test.name}</span>
        <ResultBadge result={test.result} />
        <span className="text-muted-foreground min-w-0 flex-1">{test.observation}</span>
      </li>
    );
  }
  return (
    <li className="grid gap-2 p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className="w-44 font-medium">{test.name}</span>
        <div role="radiogroup" aria-label={test.name} className="flex flex-wrap gap-1">
          {MANUAL_OPTIONS.map((option) => (
            <button
              key={option}
              type="button"
              role="radio"
              aria-checked={current.result === option}
              onClick={() => onChange({ ...current, result: option })}
              className={cn(
                "rounded-md border px-2 py-0.5 text-xs transition-colors",
                current.result === option ? RESULT_TONE[option] : "hover:bg-muted",
              )}
            >
              {RESULT_LABELS[option]}
            </button>
          ))}
        </div>
      </div>
      <Input
        aria-label={`Observación de ${test.name}`}
        placeholder="Observación (opcional)"
        value={current.observation}
        onChange={(e) => onChange({ ...current, observation: e.target.value })}
      />
    </li>
  );
}
