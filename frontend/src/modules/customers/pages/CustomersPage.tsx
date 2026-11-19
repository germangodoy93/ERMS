import { Plus, Search } from "lucide-react";
import { useDeferredValue, useState } from "react";
import { Link, useNavigate } from "react-router";

import { Pagination } from "@/components/Pagination";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatPhone } from "@/lib/format";
import { PERMS, useCan } from "@/modules/auth/permissions";
import { errorMessage } from "@/services/errors";

import { CustomerFormDialog } from "../components/CustomerFormDialog";
import { useCustomers } from "../hooks";
import { customerState, formatDocument, STATE_BADGES } from "../presentation";

const PAGE_SIZE = 20;
const ALL = "all";

export function CustomersPage() {
  const canManage = useCan(PERMS.CUSTOMERS_MANAGE);
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<string>("active");
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const deferredSearch = useDeferredValue(search);

  const customers = useCustomers({
    page,
    size: PAGE_SIZE,
    q: deferredSearch.trim() || undefined,
    is_active: status === ALL ? undefined : status === "active",
  });

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Clientes</h1>
          <p className="text-muted-foreground text-sm">
            Personas y empresas que entregan equipos al taller.
          </p>
        </div>
        {canManage && (
          <Button onClick={() => setCreating(true)}>
            <Plus /> Nuevo cliente
          </Button>
        )}
      </header>

      <div className="flex flex-wrap gap-3">
        <div className="relative min-w-56 flex-1">
          <Search className="text-muted-foreground absolute top-2.5 left-2.5 size-4" />
          <Input
            placeholder="Buscar por nombre, documento o teléfono"
            className="pl-8"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            aria-label="Buscar clientes"
          />
        </div>
        <Select
          value={status}
          onValueChange={(v) => {
            setStatus(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-40" aria-label="Filtrar por estado">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="active">Activos</SelectItem>
            <SelectItem value="inactive">Inactivos</SelectItem>
            <SelectItem value={ALL}>Todos</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Cliente</TableHead>
              <TableHead className="hidden sm:table-cell">Documento</TableHead>
              <TableHead className="hidden md:table-cell">Teléfono</TableHead>
              <TableHead>Estado</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {customers.isPending &&
              Array.from({ length: 4 }, (_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={4}>
                    <Skeleton className="h-6" />
                  </TableCell>
                </TableRow>
              ))}
            {customers.isError && (
              <TableRow>
                <TableCell colSpan={4} className="text-destructive py-8 text-center">
                  {errorMessage(customers.error)}
                </TableCell>
              </TableRow>
            )}
            {customers.data?.items.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="text-muted-foreground py-8 text-center">
                  {deferredSearch.trim()
                    ? "No hay clientes que coincidan con la búsqueda."
                    : "Aún no hay clientes registrados."}
                </TableCell>
              </TableRow>
            )}
            {customers.data?.items.map((customer) => {
              const badge = STATE_BADGES[customerState(customer)];
              return (
                <TableRow key={customer.id}>
                  <TableCell>
                    <Link to={`/clientes/${customer.id}`} className="font-medium hover:underline">
                      {customer.full_name}
                    </Link>
                    <div className="text-muted-foreground text-xs sm:hidden">
                      {formatDocument(customer)}
                    </div>
                  </TableCell>
                  <TableCell className="hidden font-mono text-sm sm:table-cell">
                    {formatDocument(customer)}
                  </TableCell>
                  <TableCell className="hidden text-sm md:table-cell">
                    {formatPhone(customer.phone)}
                  </TableCell>
                  <TableCell>
                    <StatusBadge tone={badge.tone} label={badge.label} />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {customers.data && (
        <Pagination
          page={customers.data.page}
          size={customers.data.size}
          total={customers.data.total}
          onPageChange={setPage}
        />
      )}

      {creating && (
        <CustomerFormDialog
          open
          onOpenChange={setCreating}
          onCreated={(customer) => void navigate(`/clientes/${customer.id}`)}
        />
      )}
    </div>
  );
}
