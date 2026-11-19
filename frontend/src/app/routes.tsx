import type { RouteObject } from "react-router";

import { AppLayout } from "@/layouts/AppLayout";
import { SystemStatusPage } from "@/modules/system/pages/SystemStatusPage";

import { NotFoundPage } from "./NotFoundPage";

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <SystemStatusPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
