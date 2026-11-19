import { ShieldX } from "lucide-react";
import type { ReactNode } from "react";
import { Navigate, Outlet, useLocation } from "react-router";

import { useAuthStore } from "@/stores/auth";

import { can, type PermissionCode } from "../permissions";

export function FullPageLoader() {
  return (
    <div className="flex min-h-dvh items-center justify-center" aria-busy="true">
      <p className="text-muted-foreground text-sm">Cargando ERMS…</p>
    </div>
  );
}

const CHANGE_PASSWORD_PATH = "/cambiar-contrasena";

/** Protects every private route; forces the temporary-password change first. */
export function RequireAuth() {
  const status = useAuthStore((s) => s.status);
  const mustChange = useAuthStore((s) => s.user?.must_change_password ?? false);
  const location = useLocation();

  if (status === "unknown") return <FullPageLoader />;
  if (status === "anonymous") {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  if (mustChange && location.pathname !== CHANGE_PASSWORD_PATH) {
    return <Navigate to={CHANGE_PASSWORD_PATH} replace />;
  }
  return <Outlet />;
}

export function RequirePermission({
  permission,
  children,
}: {
  permission: PermissionCode;
  children: ReactNode;
}) {
  const allowed = useAuthStore((s) => can(s.user, permission));
  if (!allowed) {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center gap-3 py-24 text-center">
        <ShieldX className="text-muted-foreground size-10" />
        <h1 className="text-xl font-semibold">Acceso restringido</h1>
        <p className="text-muted-foreground text-sm">
          Su rol no tiene permiso para ver esta sección. Si lo necesita, solicítelo a un
          administrador.
        </p>
      </div>
    );
  }
  return children;
}
