import { useQueryClient } from "@tanstack/react-query";
import { ChevronDown, KeyRound, LogOut } from "lucide-react";
import { useNavigate } from "react-router";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { signOut } from "@/modules/auth/session";
import { useAuthStore } from "@/stores/auth";

function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function UserMenu() {
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  if (!user) return null;

  const logout = async () => {
    await signOut();
    queryClient.clear();
    navigate("/login", { replace: true });
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="gap-2 px-2">
          <span className="bg-primary/10 text-primary grid size-8 place-items-center rounded-full text-xs font-semibold">
            {initials(user.full_name)}
          </span>
          <span className="hidden text-left sm:block">
            <span className="block text-sm leading-tight font-medium">{user.full_name}</span>
            <span className="text-muted-foreground block text-xs leading-tight">
              {user.roles.map((r) => r.name).join(", ")}
            </span>
          </span>
          <ChevronDown className="text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="font-normal">
          <span className="block text-sm font-medium">{user.full_name}</span>
          <span className="text-muted-foreground block truncate text-xs">{user.email}</span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => navigate("/cambiar-contrasena")}>
          <KeyRound /> Cambiar contraseña
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => void logout()}>
          <LogOut /> Cerrar sesión
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
