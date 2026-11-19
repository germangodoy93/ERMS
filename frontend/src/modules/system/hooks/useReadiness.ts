import { useQuery } from "@tanstack/react-query";

import { fetchReadiness } from "../api";

export const READINESS_QUERY_KEY = ["system", "readiness"] as const;
const REFRESH_INTERVAL_MS = 30_000;

export function useReadiness() {
  return useQuery({
    queryKey: READINESS_QUERY_KEY,
    queryFn: fetchReadiness,
    refetchInterval: REFRESH_INTERVAL_MS,
  });
}
