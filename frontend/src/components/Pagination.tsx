import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";

export function Pagination({
  page,
  size,
  total,
  onPageChange,
}: {
  page: number;
  size: number;
  total: number;
  onPageChange: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / size));
  const from = total === 0 ? 0 : (page - 1) * size + 1;
  const to = Math.min(page * size, total);
  return (
    <div className="text-muted-foreground flex items-center justify-between gap-4 text-sm">
      <span>
        {from}–{to} de {total.toLocaleString("es-CO")}
      </span>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          aria-label="Página anterior"
        >
          <ChevronLeft />
        </Button>
        <span className="tabular-nums">
          {page} / {pages}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= pages}
          aria-label="Página siguiente"
        >
          <ChevronRight />
        </Button>
      </div>
    </div>
  );
}
