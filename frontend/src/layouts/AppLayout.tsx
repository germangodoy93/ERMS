import { Menu, X } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { can } from "@/modules/auth/permissions";
import { useAuthStore } from "@/stores/auth";

import { NAVIGATION, type NavItem } from "./navigation";
import { UserMenu } from "./UserMenu";

export function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const user = useAuthStore((s) => s.user);

  const sections = NAVIGATION.map((section) => ({
    ...section,
    items: section.items.filter((item) => !item.permission || can(user, item.permission)),
  })).filter((section) => section.items.length > 0);

  return (
    <div className="flex min-h-dvh">
      <aside
        className={cn(
          "bg-sidebar text-sidebar-foreground fixed inset-y-0 left-0 z-40 flex w-64 flex-col transition-transform md:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
        aria-label="Navegación principal"
      >
        <div className="flex h-16 items-center justify-between px-5">
          <Brand />
          <button
            type="button"
            className="text-sidebar-muted hover:text-sidebar-foreground md:hidden"
            onClick={() => setMobileOpen(false)}
            aria-label="Cerrar menú"
          >
            <X className="size-5" />
          </button>
        </div>
        <nav className="flex-1 space-y-4 overflow-y-auto px-3 py-2">
          {sections.map((section, index) => (
            <div key={section.title ?? index} className="space-y-0.5">
              {section.title && (
                <p className="text-sidebar-muted px-3 pb-1 text-[11px] font-medium tracking-wider uppercase">
                  {section.title}
                </p>
              )}
              {section.items.map((item) => (
                <SidebarItem key={item.label} item={item} onNavigate={() => setMobileOpen(false)} />
              ))}
            </div>
          ))}
        </nav>
        <p className="text-sidebar-muted truncate px-5 py-4 text-xs">{user?.organization.name}</p>
      </aside>

      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 md:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden
        />
      )}

      <div className="flex min-w-0 flex-1 flex-col md:pl-64">
        <header className="bg-background/80 sticky top-0 z-20 flex h-16 items-center gap-3 border-b px-4 backdrop-blur md:px-8">
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setMobileOpen(true)}
            aria-label="Abrir menú"
          >
            <Menu />
          </Button>
          <span className="text-muted-foreground truncate text-sm">{user?.organization.name}</span>
          <div className="ml-auto">
            <UserMenu />
          </div>
        </header>
        <main className="flex-1 px-4 py-6 md:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function Brand() {
  return (
    <div className="flex items-center gap-2">
      <div className="bg-primary text-primary-foreground grid size-8 place-items-center rounded-md font-mono text-sm font-bold">
        ER
      </div>
      <span className="text-lg font-semibold tracking-tight">ERMS</span>
    </div>
  );
}

function SidebarItem({ item, onNavigate }: { item: NavItem; onNavigate: () => void }) {
  const Icon = item.icon;
  const base = "flex items-center gap-3 rounded-md px-3 py-2 text-sm";

  if (!item.to) {
    return (
      <div
        className={cn(base, "text-sidebar-muted cursor-not-allowed")}
        aria-disabled="true"
        title={`Disponible en el Sprint ${item.plannedSprint}`}
      >
        <Icon className="size-4 shrink-0" />
        <span className="flex-1 truncate">{item.label}</span>
        <span className="font-mono text-[10px] opacity-70">S{item.plannedSprint}</span>
      </div>
    );
  }

  return (
    <NavLink
      to={item.to}
      end
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          base,
          "transition-colors",
          isActive
            ? "bg-sidebar-accent text-sidebar-foreground font-medium"
            : "text-sidebar-foreground/80 hover:bg-sidebar-accent/60",
        )
      }
    >
      <Icon className="size-4 shrink-0" />
      <span className="truncate">{item.label}</span>
    </NavLink>
  );
}
