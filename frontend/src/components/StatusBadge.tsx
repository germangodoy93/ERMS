import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Tone } from "@/modules/system/presentation";

const TONE_CLASSES: Record<Tone, string> = {
  success: "border-success/30 bg-success/10 text-success",
  danger: "border-destructive/30 bg-destructive/10 text-destructive",
  neutral: "border-border bg-muted text-muted-foreground",
};

const DOT_CLASSES: Record<Tone, string> = {
  success: "bg-success",
  danger: "bg-destructive",
  neutral: "bg-muted-foreground",
};

export function StatusBadge({ tone, label }: { tone: Tone; label: string }) {
  return (
    <Badge variant="outline" className={cn("gap-1.5", TONE_CLASSES[tone])}>
      <span aria-hidden className={cn("size-1.5 rounded-full", DOT_CLASSES[tone])} />
      {label}
    </Badge>
  );
}
