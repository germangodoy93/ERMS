import { AlertCircle, PackagePlus, Plus, Search } from "lucide-react";
import { useDeferredValue, useState } from "react";
import { toast } from "sonner";

import { FormField } from "@/components/FormField";
import { SelectField } from "@/components/SelectField";
import { StatusBadge } from "@/components/StatusBadge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
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
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDateTime } from "@/lib/format";
import { PERMS, useCan } from "@/modules/auth/permissions";
import { formatMoney, parseMoney, todayInBogota } from "@/modules/workorders/presentation";
import { MOVEMENT_LABELS, PART_KIND_LABELS } from "@/modules/workshop/presentation";
import { errorMessage } from "@/services/errors";
import { PART_KINDS, type PartItem, type PartKind } from "@/types/api";

import {
  useAdjustStock,
  useMovements,
  useParts,
  useReceiveStock,
  useSavePart,
  useSaveSupplier,
  useSuppliers,
} from "../hooks";

export function InventoryPage() {
  const canManage = useCan(PERMS.INVENTORY_MANAGE);
  const [search, setSearch] = useState("");
  const [lowStock, setLowStock] = useState(false);
  const [editing, setEditing] = useState<PartItem | "new" | null>(null);
  const [detail, setDetail] = useState<PartItem | null>(null);
  const [receiving, setReceiving] = useState(false);
  const query = useDeferredValue(search.trim());
  const parts = useParts({
    q: query || undefined,
    low_stock: lowStock,
    include_inactive: canManage,
  });

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Inventario</h1>
          <p className="text-muted-foreground text-sm">
            Repuestos, existencias y movimientos. Las salidas se registran desde la reparación.
          </p>
        </div>
        {canManage && (
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setReceiving(true)}>
              <PackagePlus /> Entrada de inventario
            </Button>
            <Button onClick={() => setEditing("new")}>
              <Plus /> Nuevo repuesto
            </Button>
          </div>
        )}
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-56 flex-1">
          <Search className="text-muted-foreground absolute top-2.5 left-2.5 size-4" />
          <Input
            className="pl-8"
            placeholder="Código o nombre"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Buscar repuestos"
          />
        </div>
        <Label className="flex items-center gap-2 font-normal">
          <Checkbox checked={lowStock} onCheckedChange={(v) => setLowStock(v === true)} />
          Solo stock bajo
        </Label>
      </div>

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Repuesto</TableHead>
              <TableHead className="text-right">Existencia</TableHead>
              <TableHead className="hidden text-right md:table-cell">Precio de venta</TableHead>
              <TableHead className="hidden md:table-cell">IVA</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {parts.isPending && (
              <TableRow>
                <TableCell colSpan={4}>
                  <Skeleton className="h-6" />
                </TableCell>
              </TableRow>
            )}
            {parts.data?.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="text-muted-foreground py-8 text-center">
                  No hay repuestos.
                </TableCell>
              </TableRow>
            )}
            {parts.data?.map((part) => (
              <TableRow key={part.id} className="cursor-pointer" onClick={() => setDetail(part)}>
                <TableCell>
                  <div className="font-medium">{part.name}</div>
                  <div className="text-muted-foreground font-mono text-xs">
                    {part.sku} · {PART_KIND_LABELS[part.kind]}
                    {!part.is_active && " · inactivo"}
                  </div>
                </TableCell>
                <TableCell className="text-right">
                  <span className="mr-2 font-medium">{part.stock}</span>
                  {part.low_stock && <StatusBadge tone="danger" label="Bajo" />}
                </TableCell>
                <TableCell className="hidden text-right md:table-cell">
                  {formatMoney(part.sale_price)}
                </TableCell>
                <TableCell className="hidden text-sm md:table-cell">
                  {part.tax_rate
                    ? `19 %${part.price_includes_tax ? " incluido" : ""}`
                    : "No aplica"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <SuppliersCard canManage={canManage} />

      {editing && (
        <PartDialog
          part={editing === "new" ? undefined : editing}
          onClose={() => setEditing(null)}
        />
      )}
      {detail && (
        <PartDetailDialog
          part={detail}
          canManage={canManage}
          onEdit={() => {
            setEditing(detail);
            setDetail(null);
          }}
          onClose={() => setDetail(null)}
        />
      )}
      {receiving && <EntryDialog onClose={() => setReceiving(false)} />}
    </div>
  );
}

function PartDialog({ part, onClose }: { part?: PartItem; onClose: () => void }) {
  const save = useSavePart();
  const [sku, setSku] = useState(part?.sku ?? "");
  const [name, setName] = useState(part?.name ?? "");
  const [kind, setKind] = useState<PartKind>(part?.kind ?? "PART");
  const [cost, setCost] = useState(part ? String(Number(part.unit_cost)) : "");
  const [price, setPrice] = useState(part ? String(Number(part.sale_price)) : "");
  const [tax, setTax] = useState((part?.tax_rate ?? 0) > 0);
  const [included, setIncluded] = useState(part?.price_includes_tax ?? false);
  const [minStock, setMinStock] = useState(String(part?.min_stock ?? 0));
  const [active, setActive] = useState(part?.is_active ?? true);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setError(null);
    const unitCost = parseMoney(cost);
    const salePrice = parseMoney(price);
    if (unitCost === null || salePrice === null) return setError("Revise el costo y el precio.");
    try {
      await save.mutateAsync({
        id: part?.id,
        payload: {
          sku,
          name,
          kind,
          unit_cost: unitCost,
          sale_price: salePrice,
          tax_rate: tax ? 19 : 0,
          price_includes_tax: tax && included,
          min_stock: Number(minStock) || 0,
          is_active: active,
        },
      });
      toast.success("Repuesto guardado.");
      onClose();
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{part ? "Editar repuesto" : "Nuevo repuesto"}</DialogTitle>
          <DialogDescription>La existencia se modifica con entradas o ajustes.</DialogDescription>
        </DialogHeader>
        {error && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <div className="grid gap-3 sm:grid-cols-2">
          <FormField label="Código (SKU)" value={sku} onChange={(e) => setSku(e.target.value)} />
          <SelectField
            label="Tipo"
            value={kind}
            onChange={(v) => setKind(v as PartKind)}
            options={PART_KINDS.map((k) => ({ value: k, label: PART_KIND_LABELS[k] }))}
          />
        </div>
        <FormField label="Nombre" value={name} onChange={(e) => setName(e.target.value)} />
        <div className="grid gap-3 sm:grid-cols-3">
          <FormField
            label="Costo"
            inputMode="numeric"
            value={cost}
            onChange={(e) => setCost(e.target.value)}
          />
          <FormField
            label="Precio de venta"
            inputMode="numeric"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
          />
          <FormField
            label="Stock mínimo"
            inputMode="numeric"
            value={minStock}
            onChange={(e) => setMinStock(e.target.value.replace(/\D/g, ""))}
          />
        </div>
        <div className="flex flex-wrap gap-4">
          <Label className="flex items-center gap-2 font-normal">
            <Checkbox checked={tax} onCheckedChange={(v) => setTax(v === true)} />
            Aplica IVA 19 %
          </Label>
          {tax && (
            <Label className="flex items-center gap-2 font-normal">
              <Checkbox checked={included} onCheckedChange={(v) => setIncluded(v === true)} />
              El precio incluye IVA
            </Label>
          )}
          {part && (
            <Label className="flex items-center gap-2 font-normal">
              <Checkbox checked={active} onCheckedChange={(v) => setActive(v === true)} />
              Activo
            </Label>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            disabled={!sku.trim() || !name.trim() || save.isPending}
            onClick={() => void submit()}
          >
            Guardar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function PartDetailDialog({
  part,
  canManage,
  onEdit,
  onClose,
}: {
  part: PartItem;
  canManage: boolean;
  onEdit: () => void;
  onClose: () => void;
}) {
  const movements = useMovements(part.id);
  const adjust = useAdjustStock();
  const [counted, setCounted] = useState(String(part.stock));
  const [reason, setReason] = useState("");

  const submit = async () => {
    try {
      await adjust.mutateAsync({
        partId: part.id,
        quantity: Number(counted),
        reason: reason.trim(),
      });
      toast.success("Existencia ajustada.");
      setReason("");
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[92dvh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{part.name}</DialogTitle>
          <DialogDescription>
            {part.sku} · existencia {part.stock} · costo {formatMoney(part.unit_cost)}
          </DialogDescription>
        </DialogHeader>
        {canManage && (
          <div className="flex flex-wrap items-end gap-2 rounded-md border border-dashed p-3">
            <div className="grid gap-1.5">
              <span className="text-sm font-medium">Conteo físico</span>
              <Input
                className="w-24"
                aria-label="Cantidad contada"
                inputMode="numeric"
                value={counted}
                onChange={(e) => setCounted(e.target.value.replace(/\D/g, ""))}
              />
            </div>
            <div className="grid min-w-48 flex-1 gap-1.5">
              <span className="text-sm font-medium">Motivo</span>
              <Input
                aria-label="Motivo del ajuste"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </div>
            <Button
              variant="outline"
              disabled={counted === "" || reason.trim().length < 3 || adjust.isPending}
              onClick={() => void submit()}
            >
              Ajustar
            </Button>
          </div>
        )}
        <h3 className="text-sm font-medium">Movimientos</h3>
        {movements.isPending && <Skeleton className="h-24" />}
        <ul className="divide-y rounded-md border text-sm">
          {movements.data?.length === 0 && (
            <li className="text-muted-foreground p-3">Sin movimientos.</li>
          )}
          {movements.data?.map((m) => (
            <li key={m.id} className="flex flex-wrap items-center gap-2 p-2">
              <span className="w-24 font-medium">{MOVEMENT_LABELS[m.kind]}</span>
              <span className={m.quantity < 0 ? "text-destructive" : "text-success"}>
                {m.quantity > 0 ? `+${m.quantity}` : m.quantity}
              </span>
              <span className="text-muted-foreground">→ {m.stock_after}</span>
              <span className="text-muted-foreground">
                {[m.reference_label, m.reason].filter(Boolean).join(" · ")}
              </span>
              <span className="text-muted-foreground ml-auto text-xs">
                {formatDateTime(m.created_at)} · {m.created_by?.full_name ?? "—"}
              </span>
            </li>
          ))}
        </ul>
        <DialogFooter>
          {canManage && (
            <Button variant="outline" onClick={onEdit}>
              Editar repuesto
            </Button>
          )}
          <Button onClick={onClose}>Cerrar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface EntryLine {
  part_id: string;
  quantity: string;
  unit_cost: string;
}

function EntryDialog({ onClose }: { onClose: () => void }) {
  const parts = useParts({});
  const suppliers = useSuppliers();
  const receive = useReceiveStock();
  const [supplierId, setSupplierId] = useState("");
  const [invoice, setInvoice] = useState("");
  const [date, setDate] = useState(todayInBogota());
  const [lines, setLines] = useState<EntryLine[]>([{ part_id: "", quantity: "1", unit_cost: "" }]);
  const [error, setError] = useState<string | null>(null);

  const update = (index: number, patch: Partial<EntryLine>) =>
    setLines((current) => current.map((l, i) => (i === index ? { ...l, ...patch } : l)));

  const submit = async () => {
    setError(null);
    const payload = [];
    for (const [i, line] of lines.entries()) {
      const cost = parseMoney(line.unit_cost);
      if (!line.part_id || !Number(line.quantity) || cost === null) {
        return setError(`Revise la línea ${i + 1}.`);
      }
      payload.push({ part_id: line.part_id, quantity: Number(line.quantity), unit_cost: cost });
    }
    try {
      const entry = await receive.mutateAsync({
        supplier_id: supplierId || null,
        invoice_number: invoice.trim() || null,
        received_on: date,
        lines: payload,
      });
      toast.success(
        `Entrada registrada: ${entry.lines} línea(s), ${formatMoney(entry.total_cost)}.`,
      );
      onClose();
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[92dvh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Entrada de inventario</DialogTitle>
          <DialogDescription>Compra recibida de un proveedor.</DialogDescription>
        </DialogHeader>
        {error && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <div className="grid gap-3 sm:grid-cols-3">
          <SelectField
            label="Proveedor"
            value={supplierId}
            onChange={setSupplierId}
            emptyLabel="Sin proveedor"
            options={(suppliers.data ?? []).map((s) => ({ value: s.id, label: s.name }))}
          />
          <FormField
            label="N.º de factura"
            value={invoice}
            onChange={(e) => setInvoice(e.target.value)}
          />
          <FormField
            label="Fecha"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </div>
        {lines.map((line, index) => (
          <div key={index} className="flex flex-wrap items-end gap-2">
            <div className="min-w-56 flex-1">
              <SelectField
                label={`Repuesto ${index + 1}`}
                value={line.part_id}
                onChange={(v) => update(index, { part_id: v })}
                placeholder="Seleccione"
                options={(parts.data ?? []).map((p) => ({
                  value: p.id,
                  label: `${p.sku} · ${p.name}`,
                }))}
              />
            </div>
            <Input
              className="w-20"
              aria-label={`Cantidad ${index + 1}`}
              inputMode="numeric"
              value={line.quantity}
              onChange={(e) => update(index, { quantity: e.target.value.replace(/\D/g, "") })}
            />
            <Input
              className="w-32"
              aria-label={`Costo unitario ${index + 1}`}
              placeholder="Costo unitario"
              inputMode="numeric"
              value={line.unit_cost}
              onChange={(e) => update(index, { unit_cost: e.target.value })}
            />
          </div>
        ))}
        <Button
          variant="outline"
          size="sm"
          className="w-fit"
          onClick={() => setLines((l) => [...l, { part_id: "", quantity: "1", unit_cost: "" }])}
        >
          <Plus /> Otra línea
        </Button>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button disabled={receive.isPending} onClick={() => void submit()}>
            Registrar entrada
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function SuppliersCard({ canManage }: { canManage: boolean }) {
  const suppliers = useSuppliers();
  const save = useSaveSupplier();
  const [name, setName] = useState("");
  const [taxId, setTaxId] = useState("");

  const add = async () => {
    try {
      await save.mutateAsync({ payload: { name: name.trim(), tax_id: taxId.trim() || null } });
      setName("");
      setTaxId("");
      toast.success("Proveedor creado.");
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Proveedores</CardTitle>
        <CardDescription>Se usan al registrar entradas de inventario.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        {canManage && (
          <div className="flex flex-wrap gap-2">
            <Input
              className="min-w-48 flex-1"
              placeholder="Nombre"
              aria-label="Nombre del proveedor"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <Input
              className="w-40"
              placeholder="NIT (opcional)"
              aria-label="NIT del proveedor"
              value={taxId}
              onChange={(e) => setTaxId(e.target.value)}
            />
            <Button
              variant="outline"
              disabled={name.trim().length < 2 || save.isPending}
              onClick={() => void add()}
            >
              <Plus /> Agregar
            </Button>
          </div>
        )}
        <ul className="divide-y rounded-md border text-sm">
          {suppliers.data?.length === 0 && (
            <li className="text-muted-foreground p-3">Sin proveedores.</li>
          )}
          {suppliers.data?.map((s) => (
            <li key={s.id} className="p-2">
              {s.name}
              {s.tax_id && <span className="text-muted-foreground"> · NIT {s.tax_id}</span>}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
