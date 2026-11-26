import { Copy, ExternalLink, MessageCircle } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { SelectField } from "@/components/SelectField";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { formatPhone } from "@/lib/format";
import { errorMessage } from "@/services/errors";
import type { NoticeKind, NoticePanel, PreparedNotice } from "@/types/api";

import { usePrepareNotice } from "../hooks";
import { QrCode } from "./QrCode";

const MAX_BODY = 1500;

interface NoticeDialogProps {
  orderId: string;
  panel: NoticePanel;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function NoticeDialog({ orderId, panel, open, onOpenChange }: NoticeDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        {/* Mounted only while open, so every opening starts from the suggested notice. */}
        {open && (
          <NoticeDialogBody orderId={orderId} panel={panel} onDone={() => onOpenChange(false)} />
        )}
      </DialogContent>
    </Dialog>
  );
}

function NoticeDialogBody({
  orderId,
  panel,
  onDone,
}: {
  orderId: string;
  panel: NoticePanel;
  onDone: () => void;
}) {
  const draftOf = (kind: NoticeKind) => panel.drafts.find((d) => d.kind === kind)?.body ?? "";
  const [kind, setKind] = useState<NoticeKind>(panel.suggested);
  const [body, setBody] = useState(() => draftOf(panel.suggested));
  const [prepared, setPrepared] = useState<PreparedNotice | null>(null);
  const prepare = usePrepareNotice(orderId);

  const changeKind = (value: string) => {
    const next = value as NoticeKind;
    setKind(next);
    setBody(draftOf(next));
  };

  const submit = async () => {
    try {
      setPrepared(await prepare.mutateAsync({ kind, body }));
    } catch (error) {
      toast.error(errorMessage(error, "No se pudo preparar el aviso."));
    }
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(prepared?.notice.body ?? body);
      toast.success("Mensaje copiado.");
    } catch {
      toast.error("No se pudo copiar el mensaje.");
    }
  };

  if (prepared) {
    return (
      <>
        <DialogHeader>
          <DialogTitle>Enviar por WhatsApp</DialogTitle>
          <DialogDescription>
            Para {formatPhone(prepared.notice.phone)}. El aviso quedó registrado en la orden.
          </DialogDescription>
        </DialogHeader>
        <div className="grid justify-items-center gap-3">
          <QrCode value={prepared.url} label="Código QR para abrir el chat en el celular" />
          <p className="text-muted-foreground text-center text-sm">
            Escanee el código con la cámara del celular del taller: se abre WhatsApp Business con el
            chat y el mensaje listos. Solo falta pulsar enviar.
          </p>
        </div>
        <DialogFooter className="gap-2 sm:justify-between">
          <Button variant="outline" onClick={() => void copy()}>
            <Copy /> Copiar mensaje
          </Button>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" asChild>
              <a href={prepared.url} target="_blank" rel="noreferrer">
                <ExternalLink /> Abrir WhatsApp aquí
              </a>
            </Button>
            <Button onClick={onDone}>Listo</Button>
          </div>
        </DialogFooter>
      </>
    );
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle>Avisar por WhatsApp</DialogTitle>
        <DialogDescription>
          Para {formatPhone(panel.phone)}. Revise el mensaje antes de enviarlo.
        </DialogDescription>
      </DialogHeader>
      <div className="grid gap-4">
        <SelectField
          label="Aviso"
          value={kind}
          onChange={changeKind}
          options={panel.drafts.map((d) => ({
            value: d.kind,
            label: d.kind === panel.suggested ? `${d.label} (sugerido)` : d.label,
          }))}
        />
        <div className="grid gap-1.5">
          <Label htmlFor="notice-body">Mensaje</Label>
          <Textarea
            id="notice-body"
            rows={8}
            value={body}
            maxLength={MAX_BODY}
            onChange={(e) => setBody(e.target.value)}
          />
          <p className="text-muted-foreground text-xs">
            {body.length}/{MAX_BODY}. Solo avisos del servicio: nunca publicidad.
          </p>
        </div>
      </div>
      <DialogFooter>
        <Button onClick={() => void submit()} disabled={!body.trim() || prepare.isPending}>
          <MessageCircle /> Preparar mensaje
        </Button>
      </DialogFooter>
    </>
  );
}
