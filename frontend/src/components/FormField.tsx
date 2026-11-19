import type { ComponentProps, ReactNode } from "react";
import { useId } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface FormFieldProps extends ComponentProps<typeof Input> {
  label: string;
  error?: string;
  hint?: ReactNode;
}

/** Label + input + validation message, wired for accessibility (aria-invalid/describedby). */
export function FormField({ label, error, hint, id, ...inputProps }: FormFieldProps) {
  const generatedId = useId();
  const fieldId = id ?? generatedId;
  const messageId = `${fieldId}-message`;
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={fieldId}>{label}</Label>
      <Input
        id={fieldId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error || hint ? messageId : undefined}
        {...inputProps}
      />
      {error ? (
        <p id={messageId} className="text-destructive text-xs">
          {error}
        </p>
      ) : hint ? (
        <p id={messageId} className="text-muted-foreground text-xs">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
