import { BellRing, MessageCircle } from "lucide-react";
import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTime } from "@/lib/format";
import { errorMessage } from "@/services/errors";

import { useNoticePanel } from "../hooks";
import { NoticeDialog } from "./NoticeDialog";

const HISTORY_SHOWN = 5;

export function OrderNoticesCard({ orderId }: { orderId: string }) {
  const panel = useNoticePanel(orderId);
  const [open, setOpen] = useState(false);
  const data = panel.data;
  const suggested = data?.drafts.find((d) => d.kind === data.suggested);

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
        <CardTitle className="text-base">Avisos al cliente</CardTitle>
        {data?.can_prepare && (
          <Button size="sm" onClick={() => setOpen(true)} disabled={!data.can_whatsapp}>
            <MessageCircle /> Avisar por WhatsApp
          </Button>
        )}
      </CardHeader>
      <CardContent className="grid gap-3">
        {panel.isPending ? (
          <Skeleton className="h-16 w-full" />
        ) : panel.isError ? (
          <p className="text-destructive text-sm">{errorMessage(panel.error)}</p>
        ) : (
          data && (
            <>
              {!data.can_whatsapp && (
                <Alert>
                  <AlertDescription>{data.blocked_reason}</AlertDescription>
                </Alert>
              )}
              {data.pending && suggested && (
                <p className="flex items-center gap-2 text-sm">
                  <BellRing className="size-4 text-amber-600" />
                  Aviso pendiente: <Badge variant="secondary">{suggested.label}</Badge>
                </p>
              )}
              {data.history.length === 0 ? (
                <p className="text-muted-foreground text-sm">Todavía no hay avisos.</p>
              ) : (
                <ul className="grid gap-2">
                  {data.history.slice(0, HISTORY_SHOWN).map((notice) => (
                    <li key={notice.id} className="text-sm">
                      <details>
                        <summary className="cursor-pointer">
                          <span className="font-medium">{notice.label}</span>
                          <span className="text-muted-foreground">
                            {" "}
                            · preparado el {formatDateTime(notice.prepared_at)}
                            {notice.prepared_by ? ` por ${notice.prepared_by.full_name}` : ""}
                          </span>
                        </summary>
                        <p className="bg-muted mt-1 rounded-md p-2 whitespace-pre-wrap">
                          {notice.body}
                        </p>
                      </details>
                    </li>
                  ))}
                </ul>
              )}
              <NoticeDialog orderId={orderId} panel={data} open={open} onOpenChange={setOpen} />
            </>
          )
        )}
      </CardContent>
    </Card>
  );
}
