import { Link } from "react-router";

import { Button } from "@/components/ui/button";

export function NotFoundPage() {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-4 py-24 text-center">
      <p className="text-primary font-mono text-sm">404</p>
      <h1 className="text-2xl font-semibold tracking-tight">Página no encontrada</h1>
      <p className="text-muted-foreground text-sm">La ruta solicitada no existe en ERMS.</p>
      <Button asChild variant="outline">
        <Link to="/">Volver al inicio</Link>
      </Button>
    </div>
  );
}
