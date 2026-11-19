import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Pagination } from "@/components/Pagination";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
import { formatDateTime } from "@/lib/format";
import { errorMessage } from "@/services/errors";

import { listAuditLogs, type AuditFilters } from "../api";
import { AUDIT_ACTION_LABELS, auditActionLabel, bogotaDayBoundToUtc } from "../presentation";

const PAGE_SIZE = 25;
const ALL = "all";

export function AuditPage() {
  const [action, setAction] = useState(ALL);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [page, setPage] = useState(1);

  const filters: AuditFilters = {
    page,
    size: PAGE_SIZE,
    action: action === ALL ? undefined : action,
    date_from: bogotaDayBoundToUtc(from, "start"),
    date_to: bogotaDayBoundToUtc(to, "end"),
  };
  const logs = useQuery({
    queryKey: ["audit-logs", filters],
    queryFn: () => listAuditLogs(filters),
    placeholderData: keepPreviousData,
  });

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Auditoría</h1>
        <p className="text-muted-foreground text-sm">
          Registro inalterable de acciones sobre usuarios, roles y sesiones.
        </p>
      </header>

      <div className="flex flex-wrap items-end gap-3">
        <div className="grid gap-1.5">
          <Label>Acción</Label>
          <Select
            value={action}
            onValueChange={(v) => {
              setAction(v);
              setPage(1);
            }}
          >
            <SelectTrigger className="w-64" aria-label="Filtrar por acción">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>Todas las acciones</SelectItem>
              {Object.entries(AUDIT_ACTION_LABELS).map(([code, label]) => (
                <SelectItem key={code} value={code}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="audit-from">Desde</Label>
          <Input
            id="audit-from"
            type="date"
            value={from}
            onChange={(e) => {
              setFrom(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="audit-to">Hasta</Label>
          <Input
            id="audit-to"
            type="date"
            value={to}
            onChange={(e) => {
              setTo(e.target.value);
              setPage(1);
            }}
          />
        </div>
      </div>

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Fecha</TableHead>
              <TableHead>Acción</TableHead>
              <TableHead>Realizada por</TableHead>
              <TableHead className="hidden lg:table-cell">Detalle</TableHead>
              <TableHead className="hidden md:table-cell">IP</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {logs.isPending && (
              <TableRow>
                <TableCell colSpan={5}>
                  <Skeleton className="h-24" />
                </TableCell>
              </TableRow>
            )}
            {logs.isError && (
              <TableRow>
                <TableCell colSpan={5} className="text-destructive py-8 text-center">
                  {errorMessage(logs.error)}
                </TableCell>
              </TableRow>
            )}
            {logs.data?.items.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-muted-foreground py-8 text-center">
                  No hay registros para los filtros seleccionados.
                </TableCell>
              </TableRow>
            )}
            {logs.data?.items.map((log) => (
              <TableRow key={log.id}>
                <TableCell className="text-sm whitespace-nowrap">
                  {formatDateTime(log.created_at)}
                </TableCell>
                <TableCell>{auditActionLabel(log.action)}</TableCell>
                <TableCell className="text-sm">
                  {log.actor ? (
                    log.actor.full_name
                  ) : (
                    <span className="text-muted-foreground">Sistema / anónimo</span>
                  )}
                </TableCell>
                <TableCell className="hidden max-w-80 lg:table-cell">
                  {log.changes && (
                    <code
                      className="text-muted-foreground block truncate text-xs"
                      title={JSON.stringify(log.changes)}
                    >
                      {JSON.stringify(log.changes)}
                    </code>
                  )}
                </TableCell>
                <TableCell className="text-muted-foreground hidden font-mono text-xs md:table-cell">
                  {log.ip_address ?? "—"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {logs.data && (
        <Pagination
          page={logs.data.page}
          size={logs.data.size}
          total={logs.data.total}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}
