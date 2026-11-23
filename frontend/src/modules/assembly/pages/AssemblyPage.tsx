import { FileDown, FileSpreadsheet, Plus, Trash2, Upload } from "lucide-react";
import { useRef } from "react";
import { Link } from "react-router";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { saveBlob } from "@/lib/download";
import { formatDateTime } from "@/lib/format";
import { PERMS, useCan } from "@/modules/auth/permissions";
import { formatMoney } from "@/modules/workorders/presentation";
import { errorMessage } from "@/services/errors";
import type { CatalogImportItem } from "@/types/api";

import { downloadCostTemplate } from "../api";
import { useBuilds, useCatalog, useDeleteBuild, useImportCatalog, useUploadCosts } from "../hooks";
import { PROFILE_LABELS, parseCatalogFile } from "../presentation";

export function AssemblyPage() {
  const builds = useBuilds();
  const catalog = useCatalog();
  const remove = useDeleteBuild();
  const importer = useImportCatalog();
  const canImport = useCan(PERMS.INVENTORY_MANAGE);
  const fileInput = useRef<HTMLInputElement>(null);
  const costInput = useRef<HTMLInputElement>(null);
  const costs = useUploadCosts();

  const onTemplate = async () => {
    try {
      saveBlob(await downloadCostTemplate(), "costos-ensamble.csv");
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };

  const onCosts = async (file: File | undefined) => {
    if (!file) return;
    try {
      const r = await costs.mutateAsync(file);
      toast.success(
        `Costos actualizados: ${r.updated} con cambio y ${r.unchanged} iguales. Los precios de venta se recalcularon con el margen.`,
      );
      if (r.unknown.length) {
        toast.warning(
          `${r.unknown.length} códigos no están en el catálogo: ${r.unknown.slice(0, 5).join(", ")}`,
        );
      }
      if (r.errors.length) toast.error(r.errors.slice(0, 3).join(" "));
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      if (costInput.current) costInput.current.value = "";
    }
  };

  const onFile = async (file: File | undefined) => {
    if (!file) return;
    try {
      const items = parseCatalogFile(await file.text()) as CatalogImportItem[];
      const result = await importer.mutateAsync(items);
      toast.success(
        `Catálogo importado: ${result.created} nuevas y ${result.updated} actualizadas.`,
      );
      if (result.errors.length) {
        toast.error(`${result.errors.length} piezas rechazadas: ${result.errors[0]}`);
      }
    } catch (e) {
      toast.error(e instanceof SyntaxError ? "El archivo no es un JSON válido." : errorMessage(e));
    } finally {
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Ensamble de PC</h1>
          <p className="text-muted-foreground text-sm">
            Configure equipos a la medida con validación de compatibilidad y cree la orden de
            ensamble con su cotización. Los precios de venta son el costo del proveedor más el
            margen del taller, salvo los fijados a mano.
            {catalog.data && ` ${catalog.data.length} piezas en el catálogo.`}
          </p>
        </div>
        <div className="flex gap-2">
          {canImport && (
            <>
              <input
                ref={fileInput}
                type="file"
                accept="application/json,.json"
                className="hidden"
                aria-label="Archivo del catálogo"
                onChange={(e) => void onFile(e.target.files?.[0])}
              />
              <Button
                variant="outline"
                disabled={importer.isPending}
                onClick={() => fileInput.current?.click()}
              >
                <Upload /> Importar catálogo
              </Button>
              <Button variant="outline" onClick={() => void onTemplate()}>
                <FileDown /> Plantilla de costos
              </Button>
              <input
                ref={costInput}
                type="file"
                accept=".csv,text/csv"
                className="hidden"
                aria-label="Archivo de costos"
                onChange={(e) => void onCosts(e.target.files?.[0])}
              />
              <Button
                variant="outline"
                disabled={costs.isPending}
                onClick={() => costInput.current?.click()}
              >
                <FileSpreadsheet /> Actualizar costos
              </Button>
            </>
          )}
          <Button asChild>
            <Link to="/ensamble/nueva">
              <Plus /> Nueva configuración
            </Link>
          </Button>
        </div>
      </header>

      {builds.isPending && <Skeleton className="h-48" />}
      {builds.isError && <p className="text-destructive text-sm">{errorMessage(builds.error)}</p>}
      {builds.data && (
        <div className="overflow-x-auto rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Configuración</TableHead>
                <TableHead>Uso</TableHead>
                <TableHead className="text-right">Piezas</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Actualizada</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {builds.data.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-muted-foreground py-8 text-center">
                    Aún no hay configuraciones.
                  </TableCell>
                </TableRow>
              )}
              {builds.data.map((b) => (
                <TableRow key={b.id}>
                  <TableCell>
                    <Link to={`/ensamble/${b.id}`} className="font-medium hover:underline">
                      {b.name}
                    </Link>
                  </TableCell>
                  <TableCell>{PROFILE_LABELS[b.profile]}</TableCell>
                  <TableCell className="text-right tabular-nums">{formatMoney(b.price)}</TableCell>
                  <TableCell>
                    {b.work_order_id ? (
                      <Link to={`/ordenes/${b.work_order_id}`} className="font-mono underline">
                        {b.work_order_number}
                      </Link>
                    ) : (
                      <Badge variant="outline">Borrador</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {formatDateTime(b.updated_at)}
                  </TableCell>
                  <TableCell className="text-right">
                    {b.status === "DRAFT" && (
                      <Button
                        size="icon"
                        variant="ghost"
                        aria-label={`Borrar ${b.name}`}
                        onClick={() =>
                          remove.mutate(b.id, {
                            onError: (e) => toast.error(errorMessage(e)),
                          })
                        }
                      >
                        <Trash2 />
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
