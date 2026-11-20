import { ShieldQuestion } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";

/** Official public lookup of the Colombian negative IMEI database (Resolución CRC 3128 de
 * 2011). It has no API and requires a human security check, so ERMS only copies the IMEI and
 * opens the site; it never automates the query. */
export const IMEI_COLOMBIA_URL = "https://www.imeicolombia.com.co/";

export function ImeiCheckButton({ imei, compact = false }: { imei: string; compact?: boolean }) {
  const onClick = async () => {
    try {
      await navigator.clipboard.writeText(imei);
      toast.success("IMEI copiado. Péguelo en la consulta oficial.");
    } catch {
      toast.info(`Copie el IMEI manualmente: ${imei}`);
    }
    window.open(IMEI_COLOMBIA_URL, "_blank", "noopener,noreferrer");
  };

  return (
    <Button
      type="button"
      variant="outline"
      size={compact ? "sm" : "default"}
      onClick={() => void onClick()}
      title="Copia el IMEI y abre la consulta pública oficial de equipos reportados"
    >
      <ShieldQuestion /> Consultar en IMEI Colombia
    </Button>
  );
}
