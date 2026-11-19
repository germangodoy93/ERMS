import { useId } from "react";

import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/** Radix Select does not accept "" as an item value: this sentinel represents "none". */
const NONE = "__none__";

interface SelectFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  /** When set, adds an empty option with this label that maps to "". */
  emptyLabel?: string;
  placeholder?: string;
  error?: string;
  disabled?: boolean;
}

/** Label + Select + validation message, matching FormField. */
export function SelectField({
  label,
  value,
  onChange,
  options,
  emptyLabel,
  placeholder,
  error,
  disabled,
}: SelectFieldProps) {
  const id = useId();
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Select
        value={value === "" && emptyLabel ? NONE : value}
        onValueChange={(v) => onChange(v === NONE ? "" : v)}
        disabled={disabled}
      >
        <SelectTrigger id={id} className="w-full" aria-invalid={error ? true : undefined}>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {emptyLabel && <SelectItem value={NONE}>{emptyLabel}</SelectItem>}
          {options.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {error && <p className="text-destructive text-xs">{error}</p>}
    </div>
  );
}
