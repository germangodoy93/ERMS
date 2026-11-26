import { RotateCcw } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { errorMessage } from "@/services/errors";
import type { NoticeTemplate } from "@/types/api";

import { useNoticeTemplates, useSaveNoticeTemplate } from "../hooks";

/** Texts of the WhatsApp notices, with {fields} filled by ERMS for each order. */
export function NoticeTemplatesCard() {
  const templates = useNoticeTemplates();
  const data = templates.data;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Mensajes de WhatsApp</CardTitle>
        <CardDescription>
          Textos que ERMS propone al avisar a un cliente. Los campos entre llaves se llenan con los
          datos de cada orden. El recordatorio de equipo sin retirar se sugiere cada{" "}
          {data?.reminder_days ?? 7} días.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6">
        {templates.isPending && <Skeleton className="h-40" />}
        {templates.isError && (
          <p className="text-destructive text-sm">{errorMessage(templates.error)}</p>
        )}
        {data && (
          <>
            <details className="text-sm">
              <summary className="cursor-pointer font-medium">Campos disponibles</summary>
              <ul className="mt-2 grid gap-1 sm:grid-cols-2">
                {data.placeholders.map((p) => (
                  <li key={p.name}>
                    <code className="bg-muted rounded px-1">{`{${p.name}}`}</code>{" "}
                    <span className="text-muted-foreground">{p.description}</span>
                  </li>
                ))}
              </ul>
            </details>
            {data.templates.map((t) => (
              // Remounts with the saved text after each save or reset.
              <TemplateEditor key={`${t.kind}:${t.body}`} template={t} />
            ))}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function TemplateEditor({ template }: { template: NoticeTemplate }) {
  const [body, setBody] = useState(template.body);
  const save = useSaveNoticeTemplate();
  const id = `template-${template.kind}`;

  const run = async (value: string | null) => {
    try {
      await save.mutateAsync({ kind: template.kind, body: value });
      toast.success(value === null ? "Texto original restaurado." : "Mensaje guardado.");
    } catch (error) {
      toast.error(errorMessage(error, "No se pudo guardar el mensaje."));
    }
  };

  return (
    <div className="grid gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label htmlFor={id} className="text-sm font-medium">
          {template.label}
        </label>
        {!template.is_default && <Badge variant="outline">Personalizado</Badge>}
      </div>
      <Textarea id={id} rows={4} value={body} onChange={(e) => setBody(e.target.value)} />
      <div className="flex flex-wrap justify-end gap-2">
        {!template.is_default && (
          <Button
            variant="ghost"
            size="sm"
            disabled={save.isPending}
            onClick={() => void run(null)}
          >
            <RotateCcw /> Restaurar original
          </Button>
        )}
        <Button
          size="sm"
          disabled={save.isPending || !body.trim() || body === template.body}
          onClick={() => void run(body)}
        >
          Guardar
        </Button>
      </div>
    </div>
  );
}
