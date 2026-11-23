import { AlertCircle, Plus, Search } from "lucide-react";
import { useDeferredValue, useState } from "react";
import { useNavigate } from "react-router";
import { toast } from "sonner";

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
import { formatPhone } from "@/lib/format";
import { PERMS, useCan } from "@/modules/auth/permissions";
import { CustomerFormDialog } from "@/modules/customers/components/CustomerFormDialog";
import { useCustomers } from "@/modules/customers/hooks";
import { formatMoney } from "@/modules/workorders/presentation";
import { errorMessage } from "@/services/errors";
import type { BuildRead } from "@/types/api";

import { useOrderBuild } from "../hooks";

/** Picks the customer and creates the assembly order with its draft quote. */
export function OrderBuildDialog({ build, onClose }: { build: BuildRead; onClose: () => void }) {
  const navigate = useNavigate();
  const order = useOrderBuild();
  const canCreateCustomer = useCan(PERMS.CUSTOMERS_MANAGE);
  const [search, setSearch] = useState("");
  const [customer, setCustomer] = useState<{ id: string; name: string } | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const query = useDeferredValue(search.trim());
  const results = useCustomers({ page: 1, size: 6, q: query || undefined, is_active: true });

  const submit = async () => {
    if (!customer) return;
    setError(null);
    try {
      const created = await order.mutateAsync({ id: build.id, customerId: customer.id });
      toast.success(`Orden ${created.number} creada con su cotización en borrador.`);
      onClose();
      void navigate(`/ordenes/${created.id}`);
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Crear orden de ensamble</DialogTitle>
          <DialogDescription>
            {build.name} · piezas {formatMoney(build.price)} + mano de obra{" "}
            {formatMoney(build.labor_price)}. La orden empieza en cotización.
          </DialogDescription>
        </DialogHeader>
        {error && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {customer ? (
          <div className="flex items-center justify-between gap-2 rounded-md border p-3 text-sm">
            <span className="font-medium">{customer.name}</span>
            <Button size="sm" variant="outline" onClick={() => setCustomer(null)}>
              Cambiar
            </Button>
          </div>
        ) : (
          <div className="grid gap-2">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="text-muted-foreground absolute top-2.5 left-2.5 size-4" />
                <Input
                  className="pl-8"
                  aria-label="Buscar cliente"
                  placeholder="Buscar por nombre, documento o teléfono"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              {canCreateCustomer && (
                <Button variant="outline" onClick={() => setCreating(true)}>
                  <Plus /> Nuevo cliente
                </Button>
              )}
            </div>
            {query && (
              <ul className="divide-y rounded-md border">
                {results.data?.items.length === 0 && (
                  <li className="text-muted-foreground p-3 text-sm">Sin resultados.</li>
                )}
                {results.data?.items.map((c) => (
                  <li key={c.id}>
                    <button
                      type="button"
                      className="hover:bg-muted/60 flex w-full justify-between gap-3 p-3 text-left text-sm"
                      onClick={() => setCustomer({ id: c.id, name: c.full_name })}
                    >
                      <span className="font-medium">{c.full_name}</span>
                      <span className="text-muted-foreground">{formatPhone(c.phone)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Volver
          </Button>
          <Button disabled={!customer || order.isPending} onClick={() => void submit()}>
            Crear orden
          </Button>
        </DialogFooter>
        {creating && (
          <CustomerFormDialog
            open
            onOpenChange={setCreating}
            onCreated={(c) => setCustomer({ id: c.id, name: c.full_name })}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
