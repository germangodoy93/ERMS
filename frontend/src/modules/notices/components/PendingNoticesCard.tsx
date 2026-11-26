import { BellRing } from "lucide-react";
import { Link } from "react-router";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTime } from "@/lib/format";
import { PERMS, useCan } from "@/modules/auth/permissions";
import { errorMessage } from "@/services/errors";

import { usePendingNotices } from "../hooks";

/** Orders whose customer should be told something (quote, ready, not repaired, reminder). */
export function PendingNoticesCard() {
  const canNotify = useCan(PERMS.CUSTOMERS_NOTIFY);
  const pending = usePendingNotices(canNotify);
  if (!canNotify) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <BellRing className="size-4" /> Por avisar
          {pending.data && pending.data.length > 0 && (
            <Badge variant="secondary">{pending.data.length}</Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {pending.isPending ? (
          <Skeleton className="h-16 w-full" />
        ) : pending.isError ? (
          <p className="text-destructive text-sm">{errorMessage(pending.error)}</p>
        ) : pending.data.length === 0 ? (
          <p className="text-muted-foreground text-sm">Todos los clientes están al día.</p>
        ) : (
          <ul className="grid gap-2 text-sm">
            {pending.data.map((p) => (
              <li
                key={p.work_order_id}
                className="flex flex-wrap items-center justify-between gap-2"
              >
                <Link to={`/ordenes/${p.work_order_id}`} className="hover:underline">
                  <span className="font-mono">{p.number}</span> · {p.customer_name}
                </Link>
                <span className="flex items-center gap-2">
                  <Badge variant={p.kind === "REMINDER" ? "outline" : "secondary"}>{p.label}</Badge>
                  <span className="text-muted-foreground text-xs" title="Pendiente desde">
                    {formatDateTime(p.since)}
                  </span>
                  {!p.can_whatsapp && (
                    <span className="text-muted-foreground text-xs">(sin celular: llamar)</span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
