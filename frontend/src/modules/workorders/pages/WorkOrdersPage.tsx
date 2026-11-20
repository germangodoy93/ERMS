import { Plus, Search } from "lucide-react";
import { useDeferredValue, useState } from "react";
import { Link } from "react-router";

import { Pagination } from "@/components/Pagination";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { cn } from "@/lib/utils";
import { PERMS, useCan } from "@/modules/auth/permissions";
import { errorMessage } from "@/services/errors";
import { useAuthStore } from "@/stores/auth";

import type { WorkOrderFilters } from "../api";
import { WorkOrderStatusBadge } from "../components/WorkOrderStatusBadge";
import { useWorkOrders } from "../hooks";
import { PRIORITY_LABELS } from "../presentation";

const PAGE_SIZE = 20;

type View = "open" | "mine" | "unassigned" | "ready" | "authorization" | "all";

const VIEWS: { id: View; label: string }[] = [
  { id: "open", label: "Abiertas" },
  { id: "mine", label: "Asignadas a mí" },
  { id: "unassigned", label: "Sin asignar" },
  { id: "authorization", label: "Esperando al cliente" },
  { id: "ready", label: "Listas para entrega" },
  { id: "all", label: "Todas" },
];

function viewFilters(view: View, userId: string | undefined): Partial<WorkOrderFilters> {
  switch (view) {
    case "open":
      return { open: true };
    case "mine":
      return { open: true, technician_id: userId };
    case "unassigned":
      return { open: true, unassigned: true };
    case "authorization":
      return { status: ["PENDIENTE_AUTORIZACION"] };
    case "ready":
      return { status: ["LISTO_ENTREGA"] };
    case "all":
      return {};
  }
}

export function WorkOrdersPage() {
  const canCreate = useCan(PERMS.WORK_ORDERS_CREATE);
  const isTechnician = useCan(PERMS.WORK_ORDERS_PROGRESS);
  const userId = useAuthStore((s) => s.user?.id);
  const [view, setView] = useState<View>(isTechnician && !canCreate ? "mine" : "open");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const query = useDeferredValue(search.trim());

  const orders = useWorkOrders({
    page,
    size: PAGE_SIZE,
    q: query || undefined,
    ...viewFilters(view, userId),
  });

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Órdenes de servicio</h1>
          <p className="text-muted-foreground text-sm">
            Equipos recibidos y su avance hasta la entrega.
          </p>
        </div>
        {canCreate && (
          <Button asChild>
            <Link to="/ordenes/nueva">
              <Plus /> Nueva recepción
            </Link>
          </Button>
        )}
      </header>

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Vistas">
        {VIEWS.map((v) => (
          <Button
            key={v.id}
            role="tab"
            aria-selected={view === v.id}
            variant={view === v.id ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setView(v.id);
              setPage(1);
            }}
          >
            {v.label}
          </Button>
        ))}
      </div>

      <div className="relative max-w-xl">
        <Search className="text-muted-foreground absolute top-2.5 left-2.5 size-4" />
        <Input
          placeholder="Número, cliente, IMEI, serial o modelo"
          className="pl-8"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          aria-label="Buscar órdenes"
        />
      </div>

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Orden</TableHead>
              <TableHead>Cliente y equipo</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead className="hidden md:table-cell">Técnico</TableHead>
              <TableHead className="hidden lg:table-cell">Recibido</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {orders.isPending &&
              Array.from({ length: 4 }, (_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={5}>
                    <Skeleton className="h-6" />
                  </TableCell>
                </TableRow>
              ))}
            {orders.isError && (
              <TableRow>
                <TableCell colSpan={5} className="text-destructive py-8 text-center">
                  {errorMessage(orders.error)}
                </TableCell>
              </TableRow>
            )}
            {orders.data?.items.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-muted-foreground py-8 text-center">
                  No hay órdenes en esta vista.
                </TableCell>
              </TableRow>
            )}
            {orders.data?.items.map((order) => (
              <TableRow key={order.id}>
                <TableCell>
                  <Link
                    to={`/ordenes/${order.id}`}
                    className="font-mono text-sm font-medium hover:underline"
                  >
                    {order.number}
                  </Link>
                  {order.priority !== "NORMAL" && (
                    <Badge
                      variant="outline"
                      className={cn(
                        "ml-2",
                        order.priority === "URGENT" && "border-destructive/40 text-destructive",
                      )}
                    >
                      {PRIORITY_LABELS[order.priority]}
                    </Badge>
                  )}
                </TableCell>
                <TableCell>
                  <div className="text-sm font-medium">{order.customer.full_name}</div>
                  <div className="text-muted-foreground text-xs">
                    {order.device.manufacturer} {order.device.model}
                  </div>
                </TableCell>
                <TableCell>
                  <WorkOrderStatusBadge status={order.status} />
                </TableCell>
                <TableCell className="hidden text-sm md:table-cell">
                  {order.assigned_technician?.full_name ?? (
                    <span className="text-muted-foreground">Sin asignar</span>
                  )}
                </TableCell>
                <TableCell className="text-muted-foreground hidden text-sm lg:table-cell">
                  {formatDateTime(order.received_at)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {orders.data && (
        <Pagination
          page={orders.data.page}
          size={orders.data.size}
          total={orders.data.total}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}
