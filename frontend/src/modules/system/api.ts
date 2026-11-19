import { http } from "@/services/http";
import type { ReadinessResponse } from "@/types/api";

/**
 * GET /health/ready. A 503 still carries a valid ReadinessResponse body describing
 * which component failed, so it is treated as data rather than as an exception.
 */
export async function fetchReadiness(): Promise<ReadinessResponse> {
  const response = await http.get<ReadinessResponse>("/health/ready", {
    validateStatus: (status) => status === 200 || status === 503,
  });
  return response.data;
}
