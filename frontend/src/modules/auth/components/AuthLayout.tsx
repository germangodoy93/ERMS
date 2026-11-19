import type { ReactNode } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function AuthLayout({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <div className="bg-muted/40 flex min-h-dvh items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm space-y-6">
        <div className="flex items-center justify-center gap-2">
          <div className="bg-primary text-primary-foreground grid size-9 place-items-center rounded-md font-mono text-sm font-bold">
            ER
          </div>
          <div>
            <p className="text-lg leading-none font-semibold tracking-tight">ERMS</p>
            <p className="text-muted-foreground text-xs">Electronic Repair Management System</p>
          </div>
        </div>
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">{title}</CardTitle>
            {description && <CardDescription>{description}</CardDescription>}
          </CardHeader>
          <CardContent>{children}</CardContent>
        </Card>
      </div>
    </div>
  );
}
