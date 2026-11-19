import { isAxiosError } from "axios";

import type { ProblemDetails } from "@/types/api";

export function getProblem(error: unknown): ProblemDetails | null {
  if (isAxiosError(error) && error.response?.data && typeof error.response.data === "object") {
    const data = error.response.data as Partial<ProblemDetails>;
    if (typeof data.code === "string" && typeof data.detail === "string") {
      return data as ProblemDetails;
    }
  }
  return null;
}

/** User-facing message for any error coming from the API (Spanish, from the backend). */
export function errorMessage(error: unknown, fallback = "Ocurrió un error inesperado."): string {
  const problem = getProblem(error);
  if (problem) {
    const details = problem.errors
      ?.filter((e) => e.type === "password_policy" || e.type === "value_error")
      .map((e) => e.message.replace(/^Value error, /, ""));
    return details?.length ? `${problem.detail} ${details.join(" ")}` : problem.detail;
  }
  if (isAxiosError(error) && !error.response) {
    return "No hay conexión con el servidor.";
  }
  return fallback;
}
