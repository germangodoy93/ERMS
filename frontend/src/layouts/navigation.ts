import {
  Activity,
  ClipboardList,
  Cpu,
  LayoutDashboard,
  Package,
  Receipt,
  ShieldCheck,
  Stethoscope,
  Users,
  Wrench,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  icon: LucideIcon;
  /** Route path when the module is available; undefined while it is not yet built. */
  to?: string;
  /** Roadmap sprint shown for modules that are not available yet. */
  plannedSprint?: number;
}

export const NAVIGATION: NavItem[] = [
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
];
