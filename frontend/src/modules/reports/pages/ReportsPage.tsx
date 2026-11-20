import { FileDown, FileSpreadsheet } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { FormField } from "@/components/FormField";
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
import { formatMoney, todayInBogota } from "@/modules/workorders/presentation";
import { errorMessage } from "@/services/errors";
import { REPORT_KINDS, type ReportKind } from "@/types/api";

import { downloadReport } from "../api";
import { useReport } from "../hooks";

const LABELS: Record<ReportKind, string> = {
  income: "Ingresos",
  orders: "Órdenes",
  inventory: "Inventario",
  technicians: "Técnicos",
};

function firstOfMonth(today: string): string {
  return `${today.slice(0, 8)}01`;
}

export function ReportsPage() {
  const today = todayInBogota();
  const [kind, setKind] = useState<ReportKind>("income");
  const [from, setFrom] = useState(firstOfMonth(today));
  const [to, setTo] = useState(today);
  const valid = Boolean(from && to && from <= to);
  const report = useReport(kind, from, to, valid);

  const download = async (format: "csv" | "pdf") => {
    try {
      const blob = await downloadReport(kind, from, to, format);
      saveBlob(blob, `${kind}-${from}-${to}.${format}`);
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Reportes</h1>
        <p className="text-muted-foreground text-sm">
          Por rango de fechas (máximo un año). Descárguelos en Excel (CSV) o PDF.
        </p>
      </header>

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Tipo de reporte">
        {REPORT_KINDS.map((k) => (
          <Button
            key={k}
            role="tab"
            aria-selected={kind === k}
            size="sm"
            variant={kind === k ? "default" : "outline"}
            onClick={() => setKind(k)}
          >
            {LABELS[k]}
          </Button>
        ))}
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <FormField
          label="Desde"
          type="date"
          value={from}
          max={to}
          onChange={(e) => setFrom(e.target.value)}
        />
        <FormField
          label="Hasta"
          type="date"
          value={to}
          min={from}
          max={today}
          onChange={(e) => setTo(e.target.value)}
        />
        <div className="ml-auto flex gap-2">
          <Button variant="outline" disabled={!valid} onClick={() => void download("csv")}>
            <FileSpreadsheet /> Excel (CSV)
          </Button>
          <Button variant="outline" disabled={!valid} onClick={() => void download("pdf")}>
            <FileDown /> PDF
          </Button>
        </div>
      </div>

      {report.isPending && valid && <Skeleton className="h-48" />}
      {report.isError && <p className="text-destructive text-sm">{errorMessage(report.error)}</p>}
      {report.data && (
        <>
          <dl className="flex flex-wrap gap-x-8 gap-y-2 rounded-lg border p-4 text-sm">
            {report.data.summary.map(([label, value]) => (
              <div key={label}>
                <dt className="text-muted-foreground">{label}</dt>
                <dd className="font-semibold">{value}</dd>
              </div>
            ))}
          </dl>
          <div className="overflow-x-auto rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  {report.data.columns.map((c) => (
                    <TableHead key={c}>{c}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {report.data.rows.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={report.data.columns.length}
                      className="text-muted-foreground py-8 text-center"
                    >
                      Sin datos en el periodo.
                    </TableCell>
                  </TableRow>
                )}
                {report.data.rows.map((row, i) => (
                  <TableRow key={i}>
                    {row.map((cell, j) => (
                      <TableCell key={j} className="text-sm">
                        {report.data.money_columns.includes(j) ? formatMoney(cell) : cell}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </>
      )}
    </div>
  );
}
