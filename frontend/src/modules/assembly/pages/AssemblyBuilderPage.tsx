import { AlertCircle, ArrowLeft, Save, ShoppingCart } from "lucide-react";
import { useDeferredValue, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { toast } from "sonner";

import { FormField } from "@/components/FormField";
import { SelectField } from "@/components/SelectField";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { formatMoney, parseMoney } from "@/modules/workorders/presentation";
import { errorMessage } from "@/services/errors";
import {
  ASSEMBLY_CATEGORIES,
  USE_PROFILES,
  type AssemblyCategory,
  type BuildRead,
  type Evaluation,
  type Selection,
  type UseProfile,
} from "@/types/api";

import { CaseSideView } from "../components/CaseSideView";
import { OrderBuildDialog } from "../components/OrderBuildDialog";
import { useBuild, useCatalog, useEvaluation, useSaveBuild } from "../hooks";
import {
  CATEGORY_HINTS,
  CATEGORY_LABELS,
  EMPTY_SELECTION,
  MULTI,
  PROFILE_LABELS,
  chosen,
  clearCategory,
  selectedIds,
  specText,
  toggle,
} from "../presentation";

export function AssemblyBuilderPage() {
  const { buildId } = useParams();
  const build = useBuild(buildId);
  if (buildId && build.isPending) return <Skeleton className="h-96" />;
  if (buildId && build.isError) {
    return <p className="text-destructive text-sm">{errorMessage(build.error)}</p>;
  }
  // Remount the editor when another build is opened, so it starts from its saved values.
  return <Builder key={buildId ?? "new"} saved={build.data} />;
}

function Builder({ saved }: { saved?: BuildRead }) {
  const navigate = useNavigate();
  const catalog = useCatalog();
  const save = useSaveBuild();
  const [name, setName] = useState(saved?.name ?? "");
  const [profile, setProfile] = useState<UseProfile>(saved?.profile ?? "GAMING");
  const [selection, setSelection] = useState<Selection>(saved?.selection ?? EMPTY_SELECTION);
  const [labor, setLabor] = useState(saved ? String(Number(saved.labor_price)) : "0");
  const [notes, setNotes] = useState(saved?.notes ?? "");
  const [tab, setTab] = useState<AssemblyCategory>("CPU");
  const [search, setSearch] = useState("");
  const [onlyCompatible, setOnlyCompatible] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [ordering, setOrdering] = useState(false);
  const editable = saved?.editable ?? true;

  const request = useMemo(
    () => ({ selection, profile, candidates_for: tab }),
    [selection, profile, tab],
  );
  const evaluation = useEvaluation(request);
  const parts = useMemo(() => chosen(catalog.data ?? [], selection), [catalog.data, selection]);
  const laborValue = parseMoney(labor);
  const query = useDeferredValue(search.trim().toLowerCase());

  const change = (next: Selection) => {
    setSelection(next);
    setDirty(true);
  };

  const onSave = async () => {
    if (laborValue === null) {
      toast.error("Revise el valor de la mano de obra.");
      return;
    }
    try {
      const result = await save.mutateAsync({
        id: saved?.id,
        payload: {
          name: name.trim(),
          profile,
          selection,
          labor_price: laborValue,
          notes: notes.trim() || null,
        },
      });
      setDirty(false);
      toast.success("Configuración guardada.");
      if (!saved) void navigate(`/ensamble/${result.id}`, { replace: true });
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };

  if (catalog.isPending) return <Skeleton className="h-96" />;
  if (catalog.isError) {
    return <p className="text-destructive text-sm">{errorMessage(catalog.error)}</p>;
  }

  const ev = evaluation.data;
  const bad = new Set<AssemblyCategory>(ev?.errors.flatMap((e) => e.categories) ?? []);
  const cards = catalog.data
    .filter((p) => p.category === tab)
    .filter((p) => !query || p.name.toLowerCase().includes(query))
    .map((p) => ({
      part: p,
      on: selectedIds(selection, tab).includes(p.id),
      why: ev?.candidates[p.id],
    }))
    .filter((c) => !onlyCompatible || !c.why || c.on);
  const tabLabel = CATEGORY_LABELS[tab].toLowerCase();

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Link
            to="/ensamble"
            className="text-muted-foreground flex items-center gap-1 text-sm hover:underline"
          >
            <ArrowLeft className="size-4" /> Ensamble de PC
          </Link>
          <h1 className="text-2xl font-semibold tracking-tight">
            {saved ? saved.name : "Nueva configuración"}
          </h1>
        </div>
        {saved?.work_order_id && (
          <Button asChild variant="outline">
            <Link to={`/ordenes/${saved.work_order_id}`}>Orden {saved.work_order_number}</Link>
          </Button>
        )}
      </header>

      {!editable && (
        <Alert>
          <AlertCircle />
          <AlertDescription>
            Esta configuración ya tiene orden: se muestra solo para consulta.
          </AlertDescription>
        </Alert>
      )}

      <Stats evaluation={ev} psuWatts={Number(parts.psu?.specs.watts ?? 0)} labor={laborValue} />

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
        <div className="grid gap-4">
          <div className="bg-muted/30 h-[clamp(340px,60vh,600px)] rounded-xl border p-3">
            <CaseSideView
              parts={parts}
              modules={ev?.ram_gb ? modulesOf(parts, selection) : 0}
              bad={bad}
            />
          </div>
          {ev && <Performance evaluation={ev} />}
        </div>

        <div className="grid gap-3">
          <div className="flex gap-2 overflow-x-auto pb-1" role="tablist" aria-label="Categoría">
            {ASSEMBLY_CATEGORIES.map((c) => (
              <Button
                key={c}
                role="tab"
                size="sm"
                aria-selected={tab === c}
                variant={tab === c ? "default" : "outline"}
                onClick={() => {
                  setTab(c);
                  setSearch("");
                }}
              >
                {CATEGORY_LABELS[c]}
                {selectedIds(selection, c).length > 0 && (
                  <span className="ml-1 inline-block size-1.5 rounded-full bg-orange-500" />
                )}
              </Button>
            ))}
          </div>
          <p className="text-muted-foreground text-sm">{CATEGORY_HINTS[tab]}</p>
          {tab === "RAM" && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground text-sm">Unidades</span>
              {[1, 2, 4].map((units) => (
                <Button
                  key={units}
                  size="sm"
                  variant={selection.ram_units === units ? "default" : "outline"}
                  aria-pressed={selection.ram_units === units}
                  disabled={!editable}
                  onClick={() => change({ ...selection, ram_units: units })}
                >
                  ×{units}
                </Button>
              ))}
            </div>
          )}
          <div className="flex flex-wrap items-center gap-3">
            <Input
              className="flex-1"
              type="search"
              aria-label={`Buscar en ${tabLabel}`}
              placeholder={`Buscar ${tabLabel}`}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Label className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={onlyCompatible}
                onCheckedChange={(v) => setOnlyCompatible(v === true)}
              />
              Solo compatibles
            </Label>
          </div>
          <div className="grid max-h-[60vh] gap-2 overflow-y-auto pr-1">
            {cards.length === 0 && (
              <p className="text-muted-foreground text-sm">
                {catalog.data.length === 0
                  ? "El catálogo está vacío: impórtelo desde la lista de configuraciones."
                  : "Ninguna pieza coincide con el filtro."}
              </p>
            )}
            {cards.map(({ part, on, why }) => (
              <button
                key={part.id}
                type="button"
                aria-pressed={on}
                disabled={!editable}
                onClick={() => change(toggle(selection, part))}
                className={cn(
                  "bg-card hover:border-foreground grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-0.5 rounded-lg border p-3 text-left text-sm disabled:cursor-default",
                  on && "border-primary ring-primary ring-1",
                  why && "border-dashed",
                )}
              >
                <span className="font-medium">{part.name}</span>
                <span className="tabular-nums">{formatMoney(part.sale_price)}</span>
                <span className="text-muted-foreground col-span-2 text-xs">
                  {specText(part.category, part.specs)}
                  {part.stock > 0 ? ` · ${part.stock} en bodega` : " · por pedir"}
                </span>
                {why && (
                  <span className="text-destructive col-span-2 text-xs">No compatible: {why}</span>
                )}
              </button>
            ))}
          </div>
          {editable && selectedIds(selection, tab).length > 0 && (
            <Button
              variant="outline"
              className="w-fit"
              onClick={() => change(clearCategory(selection, tab))}
            >
              Quitar {MULTI.has(tab) ? "todas" : tabLabel}
            </Button>
          )}
        </div>
      </div>

      {ev && <Issues evaluation={ev} />}

      <section className="grid gap-4 rounded-xl border p-4">
        <h2 className="text-lg font-semibold">Datos de la configuración</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <FormField
            label="Nombre"
            placeholder="Ej.: Gamer 1440p de Ana"
            value={name}
            disabled={!editable}
            onChange={(e) => {
              setName(e.target.value);
              setDirty(true);
            }}
          />
          <SelectField
            label="Uso del equipo"
            value={profile}
            disabled={!editable}
            onChange={(v) => {
              setProfile(v as UseProfile);
              setDirty(true);
            }}
            options={USE_PROFILES.map((p) => ({ value: p, label: PROFILE_LABELS[p] }))}
          />
          <FormField
            label="Mano de obra del ensamble"
            inputMode="numeric"
            value={labor}
            disabled={!editable}
            error={laborValue === null ? "Valor inválido" : undefined}
            onChange={(e) => {
              setLabor(e.target.value);
              setDirty(true);
            }}
          />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="build-notes">Notas (opcional)</Label>
          <Textarea
            id="build-notes"
            value={notes}
            disabled={!editable}
            onChange={(e) => {
              setNotes(e.target.value);
              setDirty(true);
            }}
          />
        </div>
        {editable && (
          <div className="flex flex-wrap justify-end gap-2">
            <Button
              variant="outline"
              disabled={name.trim().length < 2 || save.isPending}
              onClick={() => void onSave()}
            >
              <Save /> Guardar
            </Button>
            <Button
              disabled={!saved || dirty || !saved.evaluation.ready}
              title={
                !saved || dirty
                  ? "Guarde la configuración primero"
                  : !saved.evaluation.ready
                    ? "La configuración debe estar completa y sin incompatibilidades"
                    : undefined
              }
              onClick={() => setOrdering(true)}
            >
              <ShoppingCart /> Crear orden
            </Button>
          </div>
        )}
      </section>
      {ordering && saved && <OrderBuildDialog build={saved} onClose={() => setOrdering(false)} />}
    </div>
  );
}

function modulesOf(parts: ReturnType<typeof chosen>, selection: Selection): number {
  return parts.ram ? Number(parts.ram.specs.modules) * selection.ram_units : 0;
}

function Stats({
  evaluation,
  psuWatts,
  labor,
}: {
  evaluation?: Evaluation;
  psuWatts: number;
  labor: string | null;
}) {
  const watts = evaluation?.watts ?? 0;
  const rec = evaluation?.recommended_psu_w ?? 0;
  const pct = psuWatts ? Math.min(100, (watts / psuWatts) * 100) : Math.min(100, watts / 12);
  const total = Number(evaluation?.price ?? 0) + Number(labor ?? 0);
  const state = !evaluation
    ? ["text-muted-foreground", "Calculando…"]
    : evaluation.errors.length
      ? [
          "text-destructive",
          `${evaluation.errors.length} ${evaluation.errors.length > 1 ? "incompatibilidades" : "incompatibilidad"}`,
        ]
      : evaluation.missing.length
        ? ["text-muted-foreground", `Faltan ${evaluation.missing.length} piezas`]
        : evaluation.warnings.length
          ? ["text-warning", "Compatible, con avisos"]
          : ["text-success", "Listo para ensamblar"];
  return (
    <section className="grid gap-4 border-y py-4 sm:grid-cols-3" aria-label="Resumen">
      <div>
        <p className="text-muted-foreground text-xs">Total</p>
        <p className="text-2xl font-semibold tabular-nums">{formatMoney(String(total))}</p>
        <p className="text-muted-foreground text-xs">
          Piezas {formatMoney(evaluation?.price ?? "0")} · mano de obra {formatMoney(labor ?? "0")}
        </p>
      </div>
      <div>
        <p className="text-muted-foreground text-xs">Consumo estimado</p>
        <p className="text-2xl font-semibold tabular-nums">{watts} W</p>
        <div className="bg-muted relative my-1.5 h-2 rounded">
          <div
            className={cn(
              "h-full rounded transition-[width]",
              psuWatts && watts > psuWatts ? "bg-destructive" : "bg-foreground",
            )}
            style={{ width: `${pct}%` }}
          />
          {psuWatts > 0 && watts > 0 && (
            <span
              className="absolute -top-1 -bottom-1 w-0.5 bg-orange-500"
              style={{ left: `${Math.min(99, (rec / psuWatts) * 100)}%` }}
            />
          )}
        </div>
        <p className="text-muted-foreground text-xs">
          {psuWatts
            ? `Fuente de ${psuWatts} W · recomendado ${rec} W (marca naranja)`
            : watts
              ? `Fuente recomendada: ${rec} W`
              : "Elija piezas para calcularlo"}
        </p>
      </div>
      <div>
        <p className="text-muted-foreground text-xs">Estado</p>
        <p className={cn("text-2xl font-semibold", state[0])}>{state[1]}</p>
      </div>
    </section>
  );
}

function Performance({ evaluation }: { evaluation: Evaluation }) {
  return (
    <div className="grid gap-2">
      {[
        ["Juegos", evaluation.gaming_index],
        ["Trabajo pesado", evaluation.work_index],
      ].map(([label, value]) => (
        <div
          key={label}
          className="grid grid-cols-[8rem_minmax(0,1fr)_2.5rem] items-center gap-3 text-sm"
        >
          <span>{label}</span>
          <div className="bg-muted h-2 rounded">
            <div className="h-full rounded bg-orange-500" style={{ width: `${value}%` }} />
          </div>
          <b className="text-right tabular-nums">{value}</b>
        </div>
      ))}
      <p className="text-muted-foreground text-xs">
        Índice orientativo de 0 a 100 según procesador, gráfica y memoria.
      </p>
    </div>
  );
}

function Issues({ evaluation }: { evaluation: Evaluation }) {
  const rows = [
    ...evaluation.errors.map((e) => ({ tone: "Error", cls: "text-destructive", text: e.message })),
    ...evaluation.warnings.map((w) => ({ tone: "Aviso", cls: "text-warning", text: w.message })),
  ];
  if (evaluation.missing.length) {
    rows.push({
      tone: "Falta",
      cls: "text-muted-foreground",
      text: evaluation.missing.map((c) => CATEGORY_LABELS[c]).join(", "),
    });
  }
  return (
    <section className="grid gap-2">
      <h2 className="text-lg font-semibold">Compatibilidad</h2>
      <ul className="grid gap-1.5">
        {rows.length === 0 && (
          <li className="bg-muted/40 rounded-md p-2.5 text-sm">
            <Badge variant="outline" className="text-success mr-2">
              Listo
            </Badge>
            Todas las piezas son compatibles.
          </li>
        )}
        {rows.map((r) => (
          <li key={r.tone + r.text} className="bg-muted/40 rounded-md p-2.5 text-sm">
            <b className={cn("mr-2", r.cls)}>{r.tone}</b>
            {r.text}
          </li>
        ))}
      </ul>
    </section>
  );
}
