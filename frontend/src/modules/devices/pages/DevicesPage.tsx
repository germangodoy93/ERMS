import { Search } from "lucide-react";
import { useDeferredValue, useState } from "react";
import { Link } from "react-router";

import { Pagination } from "@/components/Pagination";
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
import { errorMessage } from "@/services/errors";
import { ImeiCheckButton } from "@/modules/devices/components/ImeiCheckButton";

import { useSearchDevices } from "../hooks";

const PAGE_SIZE = 20;
const MIN_QUERY = 3;

export function DevicesPage() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const query = useDeferredValue(search.trim());
  const devices = useSearchDevices(query, page, PAGE_SIZE);
  const ready = query.length >= MIN_QUERY;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Dispositivos</h1>
        <p className="text-muted-foreground text-sm">
          Busque un equipo por IMEI, serial o modelo. Los equipos se registran desde la ficha del
          cliente.
        </p>
      </header>

      <div className="relative max-w-xl">
        <Search className="text-muted-foreground absolute top-2.5 left-2.5 size-4" />
        <Input
          placeholder="IMEI, serial o modelo (mínimo 3 caracteres)"
          className="pl-8"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          aria-label="Buscar equipos"
        />
      </div>

      {ready && (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Equipo</TableHead>
                <TableHead className="hidden sm:table-cell">IMEI / Serial</TableHead>
                <TableHead>Cliente</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {devices.isPending && (
                <TableRow>
                  <TableCell colSpan={3}>
                    <Skeleton className="h-6" />
                  </TableCell>
                </TableRow>
              )}
              {devices.isError && (
                <TableRow>
                  <TableCell colSpan={3} className="text-destructive py-6 text-center">
                    {errorMessage(devices.error)}
                  </TableCell>
                </TableRow>
              )}
              {devices.data?.items.length === 0 && (
                <TableRow>
                  <TableCell colSpan={3} className="text-muted-foreground py-6 text-center">
                    No se encontraron equipos.
                  </TableCell>
                </TableRow>
              )}
              {devices.data?.items.map((device) => (
                <TableRow key={device.id}>
                  <TableCell>
                    <div className="font-medium">
                      {device.model.manufacturer.name} {device.model.name}
                    </div>
                    <div className="text-muted-foreground text-xs">
                      {device.model.category.name}
                    </div>
                  </TableCell>
                  <TableCell className="hidden font-mono text-xs sm:table-cell">
                    {device.imei && (
                      <div className="flex flex-col items-start gap-1">
                        <span>IMEI {device.imei}</span>
                        <ImeiCheckButton imei={device.imei} compact />
                      </div>
                    )}
                    {device.serial_number && <div>S/N {device.serial_number}</div>}
                  </TableCell>
                  <TableCell>
                    <Link to={`/clientes/${device.customer_id}`} className="hover:underline">
                      {device.customer_name}
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      {ready && devices.data && (
        <Pagination
          page={devices.data.page}
          size={devices.data.size}
          total={devices.data.total}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}
