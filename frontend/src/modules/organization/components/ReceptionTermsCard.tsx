import { AlertCircle, AlertTriangle, CheckCircle2, FileText } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { formatDateTime } from "@/lib/format";
import { usePublishReceptionTerms, useReceptionTerms } from "@/modules/workorders/hooks";
import { errorMessage } from "@/services/errors";

const MIN_LENGTH = 100;

/** Conditions printed on every reception act; versioned like the privacy policy. */
export function ReceptionTermsCard() {
  const current = useReceptionTerms();
  const publish = usePublishReceptionTerms();
  const [content, setContent] = useState<string | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const terms = current.data?.terms;
  const editing = content !== null;

  const startEditing = () => {
    setContent(terms?.content ?? current.data?.template ?? "");
    setReviewed(false);
    setError(null);
  };

  const onPublish = async () => {
    if (content === null) return;
    setError(null);
    try {
      const published = await publish.mutateAsync(content);
      toast.success(`Condiciones versión ${published.version} publicadas.`);
      setContent(null);
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Condiciones del acta de recepción</CardTitle>
        <CardDescription>
          Se imprimen en cada acta. Cada orden guarda la versión que firmó el cliente.
        </CardDescription>
        {!editing && (
          <CardAction>
            <Button variant="outline" onClick={startEditing} disabled={current.isPending}>
              <FileText /> {terms ? "Publicar nueva versión" : "Revisar y publicar"}
            </Button>
          </CardAction>
        )}
      </CardHeader>
      <CardContent className="grid gap-4">
        {current.isPending && <Skeleton className="h-16" />}
        {current.data &&
          (terms ? (
            <Alert>
              <CheckCircle2 className="text-success" />
              <AlertTitle>Versión {terms.version} vigente</AlertTitle>
              <AlertDescription>
                Publicada el {formatDateTime(terms.published_at)}.
              </AlertDescription>
            </Alert>
          ) : (
            <Alert variant="destructive">
              <AlertTriangle />
              <AlertTitle>Sin condiciones publicadas</AlertTitle>
              <AlertDescription>
                Mientras no se publiquen, no se pueden recibir equipos.
              </AlertDescription>
            </Alert>
          ))}
        {editing && (
          <div className="grid gap-3">
            <Alert>
              <AlertTriangle />
              <AlertTitle>Texto base, no es asesoría legal</AlertTitle>
              <AlertDescription>
                Ajústelo a las condiciones reales de su taller (plazos, garantía, retiro de
                equipos). Lo ideal es que lo revise un abogado.
              </AlertDescription>
            </Alert>
            {error && (
              <Alert variant="destructive">
                <AlertCircle />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <div className="flex justify-end">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setContent(current.data?.template ?? "")}
              >
                Restablecer plantilla
              </Button>
            </div>
            <Textarea
              aria-label="Texto de las condiciones"
              className="max-h-[32rem] min-h-72 font-mono text-xs"
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
            <Label className="flex items-center gap-2 font-normal">
              <Checkbox checked={reviewed} onCheckedChange={(v) => setReviewed(v === true)} />
              Revisé las condiciones.
            </Label>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setContent(null)}>
                Cancelar
              </Button>
              <Button
                onClick={() => void onPublish()}
                disabled={!reviewed || content.trim().length < MIN_LENGTH || publish.isPending}
              >
                {publish.isPending ? "Publicando…" : "Publicar"}
              </Button>
            </div>
          </div>
        )}
        {!editing && terms && (
          <details className="rounded-md border p-3 text-sm">
            <summary className="cursor-pointer font-medium">Ver texto vigente</summary>
            <p className="mt-3 whitespace-pre-wrap">{terms.content}</p>
          </details>
        )}
      </CardContent>
    </Card>
  );
}
