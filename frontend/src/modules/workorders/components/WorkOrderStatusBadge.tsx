import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { WorkOrderStatus } from "@/types/api";

import { STATUS_LABELS, statusTone, type StatusTone } from "../presentation";

const TONES: Record<StatusTone, string> = {
  neutral: "border-border bg-muted text-muted-foreground",
  info: "border-primary/30 bg-primary/10 text-primary",
  warning: "border-warning/40 bg-warning/15 text-foreground",
  success: "border-success/30 bg-success/10 text-success",
  danger: "border-destructive/30 bg-destructive/10 text-destructive",
};

export function WorkOrderStatusBadge({ status }: { status: WorkOrderStatus }) {
  return (
    <Badge variant="outline" className={cn("whitespace-nowrap", TONES[statusTone(status)])}>
      {STATUS_LABELS[status]}
    </Badge>
  );
}
