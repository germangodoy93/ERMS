import { AlertCircle, Download, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTime } from "@/lib/format";
import { errorMessage } from "@/services/errors";
import type { AgentPairing } from "@/types/api";

import { useDiagnostic } from "../hooks";
import { remaining } from "../presentation";

const POLL_MS = 5000;

/** Shows the one-time code while polling the diagnostic until the agent reports. */
export function AgentDialog({
  orderId,
  pairing,
  error,
  startedAt,
  onClose,
}: {
  orderId: string;
  pairing: AgentPairing | undefined;
  error: unknown;
  startedAt: string | null;
  onClose: () => void;
}) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const diagnostic = useDiagnostic(orderId, { pollMs: POLL_MS });
  const reportedAt = diagnostic.data?.agent_reported_at ?? null;
  const received = Boolean(reportedAt && (!startedAt || reportedAt > startedAt));

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Diagnóstico con agente</DialogTitle>
          <DialogDescription>
            Ejecute el agente en el computador del cliente y escriba este código.
          </DialogDescription>
        </DialogHeader>

        {error ? (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>{errorMessage(error)}</AlertDescription>
          </Alert>
        ) : !pairing ? (
          <Skeleton className="h-24" />
        ) : received ? (
          <Alert>
            <AlertTitle>Resultados recibidos</AlertTitle>
            <AlertDescription>
              El agente envió los datos el {formatDateTime(reportedAt)}. Ya aparecen en la lista de
              pruebas.
            </AlertDescription>
          </Alert>
        ) : (
          <div className="grid gap-4">
            <div className="bg-muted rounded-lg py-4 text-center">
              <p
                className="font-mono text-4xl font-semibold tracking-[0.2em]"
                aria-label="Código de emparejamiento"
              >
                {pairing.code}
              </p>
              <p className="text-muted-foreground mt-1 text-sm">
                Vence en {remaining(pairing.expires_at, now)} · un solo uso
              </p>
            </div>
            <ol className="list-decimal space-y-1 pl-5 text-sm">
              <li>
                Descargue el agente en el computador del cliente y ábralo. Windows mostrará "Windows
                protegió su PC": elija <em>Más información → Ejecutar de todas formas</em> (el
                agente no tiene firma digital).
              </li>
              <li>
                Para incluir el SMART de los discos, ábralo con clic derecho →{" "}
                <em>Ejecutar como administrador</em>.
              </li>
              <li>Confirme la autorización del cliente y escriba el código.</li>
              <li>Esta ventana se actualiza sola cuando lleguen los resultados.</li>
            </ol>
            <Alert>
              <ShieldAlert />
              <AlertDescription>
                El agente solo lee información técnica del hardware. No accede a archivos ni realiza
                cambios en el equipo.
              </AlertDescription>
            </Alert>
          </div>
        )}

        <DialogFooter>
          {pairing && !received && (
            <Button variant="outline" asChild>
              <a href={pairing.download_url} target="_blank" rel="noreferrer">
                <Download /> Descargar agente
              </a>
            </Button>
          )}
          <Button onClick={onClose}>{received ? "Ver resultados" : "Cerrar"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
