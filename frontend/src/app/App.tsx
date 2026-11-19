import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { createBrowserRouter, RouterProvider } from "react-router";
import { Toaster } from "sonner";

import { restoreSession } from "@/modules/auth/session";

import { routes } from "./routes";

const router = createBrowserRouter(routes);

export function App() {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { staleTime: 10_000, retry: 1, refetchOnWindowFocus: true } },
      }),
  );

  useEffect(() => {
    void restoreSession();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster richColors position="top-right" closeButton />
    </QueryClientProvider>
  );
}
