import {
  Activity,
  ClipboardList,
  Cpu,
  History,
  LayoutDashboard,
  Package,
  Receipt,
  ShieldCheck,
  Stethoscope,
  UserCog,
  Users,
  Wrench,
  type LucideIcon,
} from "lucide-react";

import { PERMS, type PermissionCode } from "@/modules/auth/permissions";

export interface NavItem {
  label: string;
  icon: LucideIcon;
  /** Route path when the module is available; undefined while it is not yet built. */
  to?: string;
  /** Roadmap sprint shown for modules that are not available yet. */
  plannedSprint?: number;
  /** Hidden unless the user has this permission. */
  permission?: PermissionCode;
}

export interface NavSection {
  title?: string;
  items: NavItem[];
}

export const NAVIGATION: NavSection[] = [
  {
    items: [
      { label: "Estado del sistema", icon: Activity, to: "/" },
      { label: "Dashboard", icon: LayoutDashboard, plannedSprint: 6 },
      { label: "Órdenes de servicio", icon: ClipboardList, plannedSprint: 3 },
      { label: "Clientes", icon: Users, plannedSprint: 2 },
      { label: "Dispositivos", icon: Cpu, plannedSprint: 2 },
      { label: "Diagnósticos", icon: Stethoscope, plannedSprint: 4 },
      { label: "Reparaciones", icon: Wrench, plannedSprint: 5 },
      { label: "Inventario", icon: Package, plannedSprint: 5 },
      { label: "Cotizaciones y pagos", icon: Receipt, plannedSprint: 5 },
      { label: "Garantías", icon: ShieldCheck, plannedSprint: 6 },
    ],
  },
  {
    title: "Administración",
    items: [
      { label: "Usuarios", icon: UserCog, to: "/usuarios", permission: PERMS.USERS_READ },
      { label: "Roles y permisos", icon: ShieldCheck, to: "/roles", permission: PERMS.USERS_READ },
      { label: "Auditoría", icon: History, to: "/auditoria", permission: PERMS.AUDIT_READ },
    ],
  },
];
