import { defineConfig, devices } from "@playwright/test";

// Runs against an already running stack (docker compose in CI, Vite + uvicorn locally).
// E2E_BASE_URL defaults to the Vite dev server, which proxies /api to the backend.
export default defineConfig({
  testDir: "./tests",
  timeout: 180_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: Boolean(process.env.CI),
  // "github" turns failures into annotations, readable without signing in to GitHub.
  reporter: process.env.CI ? [["list"], ["github"], ["html", { open: "never" }]] : [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173",
    locale: "es-CO",
    timezoneId: "America/Bogota",
    actionTimeout: 15_000,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
