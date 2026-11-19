import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { createBrowserRouter, RouterProvider } from "react-router";

import { routes } from "./routes";

const router = createBrowserRouter(routes);

export function App() {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { staleTime: 10_000, retry: 1, refetchOnWindowFocus: true } },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
