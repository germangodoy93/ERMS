/** Only same-app relative paths are accepted as redirect targets (prevents open redirects). */
export function safeNextPath(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
}
