import { Check, Lock, PackageMinus } from "lucide-react";
import { Link } from "react-router";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { errorMessage } from "@/services/errors";
import type { WorkOrder } from "@/types/api";

import { useChecklist, useChecklistActions } from "../hooks";

/** Assembly steps in the real order; a step can only be done after its prerequisites. */
export function AssemblyChecklistPanel({ order }: { order: WorkOrder }) {
  const checklist = useChecklist(order.id);
  const actions = useChecklistActions(order.id);
  if (checklist.isPending) return <Skeleton className="h-40" />;
  if (checklist.isError) {
    return <p className="text-destructive text-sm">{errorMessage(checklist.error)}</p>;
  }
  const data = checklist.data;
  const done = data.steps.filter((s) => s.done).length;
  const run = (action: Promise<unknown>) =>
    action.catch((e: unknown) => toast.error(errorMessage(e)));

  return (
    <div className="grid gap-3 text-sm">
      <p className="text-muted-foreground">
        Configuración{" "}
        <Link to={`/ensamble/${data.build_id}`} className="font-medium underline">
          {data.build_name}
        </Link>{" "}
        · {done} de {data.steps.length} pasos
      </p>
      {!data.parts_consumed ? (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-dashed p-3">
          <span>
            Primero descuente del inventario todas las piezas de la configuración (todas o ninguna).
          </span>
          <Button
            size="sm"
            disabled={!data.can_work || actions.consume.isPending}
            onClick={() => void run(actions.consume.mutateAsync())}
          >
            <PackageMinus /> Descontar piezas
          </Button>
        </div>
      ) : (
        <p className="text-success">Piezas descontadas del inventario.</p>
      )}
      <ol className="grid gap-1.5">
        {data.steps.map((step, i) => (
          <li key={step.code}>
            <button
              type="button"
              disabled={step.done || !data.can_work || actions.step.isPending}
              onClick={() => void run(actions.step.mutateAsync(step.code))}
              className={cn(
                "flex w-full items-center gap-3 rounded-md border p-2.5 text-left",
                step.done ? "opacity-60" : "hover:border-foreground",
              )}
            >
              <span className="text-muted-foreground w-5 text-right tabular-nums">{i + 1}.</span>
              {step.done ? (
                <Check className="text-success size-4" />
              ) : step.blocked_reason ? (
                <Lock className="text-muted-foreground size-4" />
              ) : (
                <span className="size-4" />
              )}
              <span className="flex-1">
                {step.title}
                {!step.done && step.blocked_reason && (
                  <span className="text-muted-foreground block text-xs">{step.blocked_reason}</span>
                )}
              </span>
            </button>
          </li>
        ))}
      </ol>
      {!data.can_work && (
        <p className="text-muted-foreground text-xs">
          Los pasos se marcan con la orden en reparación.
        </p>
      )}
    </div>
  );
}
