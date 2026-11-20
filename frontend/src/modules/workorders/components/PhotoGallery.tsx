import { useQuery } from "@tanstack/react-query";
import { Camera, FlaskConical, Trash2 } from "lucide-react";
import { useEffect, useMemo, useRef } from "react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PERMS, useCan } from "@/modules/auth/permissions";
import { errorMessage } from "@/services/errors";
import type { Photo, WorkOrder } from "@/types/api";

import { getPhotoContent } from "../api";
import { useDeletePhoto, usePhotos, useUploadPhoto } from "../hooks";

/** Photos are fetched with the auth header and shown through object URLs. */
function PhotoThumb({
  orderId,
  photo,
  onDelete,
}: {
  orderId: string;
  photo: Photo;
  onDelete?: () => void;
}) {
  const blob = useQuery({
    queryKey: ["work-orders", "photo", orderId, photo.id],
    queryFn: () => getPhotoContent(orderId, photo.id),
    staleTime: Infinity,
    retry: false,
  });
  const url = useMemo(() => (blob.data ? URL.createObjectURL(blob.data) : null), [blob.data]);
  useEffect(() => () => void (url && URL.revokeObjectURL(url)), [url]);

  return (
    <figure className="group relative overflow-hidden rounded-md border">
      {url ? (
        <a href={url} target="_blank" rel="noreferrer">
          <img src={url} alt={photo.file_name} className="aspect-square w-full object-cover" />
        </a>
      ) : blob.isError ? (
        <div className="text-muted-foreground grid aspect-square place-items-center p-2 text-center text-xs">
          {errorMessage(blob.error)}
        </div>
      ) : (
        <Skeleton className="aspect-square w-full" />
      )}
      {onDelete && (
        <Button
          variant="destructive"
          size="icon"
          className="absolute top-1 right-1 size-7 opacity-80"
          aria-label={`Eliminar ${photo.file_name}`}
          onClick={onDelete}
        >
          <Trash2 className="size-3.5" />
        </Button>
      )}
    </figure>
  );
}

export function PhotoGallery({ order }: { order: WorkOrder }) {
  const canCreate = useCan(PERMS.WORK_ORDERS_CREATE);
  const canProgress = useCan(PERMS.WORK_ORDERS_PROGRESS);
  const canTake = canCreate || canProgress;
  const photos = usePhotos(order.id);
  const upload = useUploadPhoto(order.id);
  const remove = useDeletePhoto(order.id);
  const input = useRef<HTMLInputElement>(null);
  const editable = canTake && order.status !== "ENTREGADO" && order.customer_allows_photos;
  const full = (photos.data?.items.length ?? 0) >= (photos.data?.max_photos ?? Infinity);

  const onFiles = async (files: FileList | null) => {
    for (const file of Array.from(files ?? [])) {
      try {
        await upload.mutateAsync(file);
      } catch (e) {
        toast.error(`${file.name}: ${errorMessage(e)}`);
      }
    }
    if (input.current) input.current.value = "";
  };

  return (
    <div className="grid gap-3">
      {photos.data?.demo && (
        <Alert>
          <FlaskConical />
          <AlertTitle>Modo demostración</AlertTitle>
          <AlertDescription>
            Las fotos se guardan en el disco del servidor y pueden perderse al redesplegar. Falta
            elegir el proveedor de almacenamiento definitivo.
          </AlertDescription>
        </Alert>
      )}
      {!order.customer_allows_photos && (
        <p className="text-muted-foreground text-sm">
          El cliente no ha autorizado fotografías del equipo. Regístrelo en su ficha, pestaña
          Autorizaciones.
        </p>
      )}
      {editable && (
        <div>
          <input
            ref={input}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            capture="environment"
            multiple
            hidden
            onChange={(e) => void onFiles(e.target.files)}
          />
          <Button
            variant="outline"
            onClick={() => input.current?.click()}
            disabled={upload.isPending || full}
          >
            <Camera /> {upload.isPending ? "Subiendo…" : "Agregar fotos"}
          </Button>
          <p className="text-muted-foreground mt-1 text-xs">
            Se eliminan los metadatos (incluida la ubicación GPS) y se reducen a 2048 px.
          </p>
        </div>
      )}
      {photos.isPending && <Skeleton className="h-32" />}
      {photos.data && photos.data.items.length === 0 && (
        <p className="text-muted-foreground text-sm">Sin fotos.</p>
      )}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-6">
        {photos.data?.items.map((photo) => (
          <PhotoThumb
            key={photo.id}
            orderId={order.id}
            photo={photo}
            onDelete={
              editable
                ? () =>
                    void remove
                      .mutateAsync(photo.id)
                      .catch((e: unknown) => toast.error(errorMessage(e)))
                : undefined
            }
          />
        ))}
      </div>
    </div>
  );
}
