import { useQuery } from "@tanstack/react-query";
import QRCode from "qrcode";

import { Skeleton } from "@/components/ui/skeleton";

/**
 * QR generated in the browser (no external service sees the customer's number or message).
 * SVG output needs no canvas, so it also renders in tests.
 */
export function QrCode({ value, label }: { value: string; label: string }) {
  const svg = useQuery({
    queryKey: ["qr", value],
    queryFn: () => QRCode.toString(value, { type: "svg", errorCorrectionLevel: "L", margin: 1 }),
    staleTime: Infinity,
    gcTime: 60_000,
    retry: false,
  });
  if (svg.isError) {
    return (
      <p className="text-muted-foreground max-w-56 text-center text-sm">
        El mensaje es demasiado largo para un código QR. Acórtelo o use «Abrir WhatsApp».
      </p>
    );
  }
  if (!svg.data) return <Skeleton className="size-56" />;
  return (
    <img
      src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg.data)}`}
      alt={label}
      className="size-56 rounded-md border bg-white p-2"
    />
  );
}
