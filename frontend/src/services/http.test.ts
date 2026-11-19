import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { AxiosError } from "axios";

import { useAuthStore } from "@/stores/auth";

import { http, refreshAccessToken } from "./http";

type Handler = (config: InternalAxiosRequestConfig) => { status: number; data?: unknown };

function respond(config: InternalAxiosRequestConfig, status: number, data: unknown = {}) {
  const response = { status, data, headers: {}, config, statusText: "" } as AxiosResponse;
  if (status >= 400) {
    throw new AxiosError("error", String(status), config, null, response);
  }
  return response;
}

function useAdapter(handler: Handler) {
  const calls: InternalAxiosRequestConfig[] = [];
  const adapter: AxiosAdapter = async (config) => {
    calls.push(config);
    const { status, data } = handler(config);
    return respond(config, status, data);
  };
  http.defaults.adapter = adapter;
  return calls;
}

describe("http client", () => {
  beforeEach(() => {
    useAuthStore.setState({ status: "authenticated", accessToken: "old-token", user: null });
  });

  it("sends the access token as a bearer header", async () => {
    const calls = useAdapter(() => ({ status: 200 }));
    await http.get("/users");
    expect(calls[0]?.headers.get("Authorization")).toBe("Bearer old-token");
  });

  it("refreshes once and retries when the access token expired", async () => {
    const calls = useAdapter((config) => {
      if (config.url === "/auth/refresh") return { status: 200, data: { access_token: "new" } };
      const auth = config.headers.get("Authorization");
      return auth === "Bearer new" ? { status: 200, data: "ok" } : { status: 401 };
    });

    const [a, b] = await Promise.all([http.get("/users"), http.get("/roles")]);

    expect(a.data).toBe("ok");
    expect(b.data).toBe("ok");
    expect(calls.filter((c) => c.url === "/auth/refresh")).toHaveLength(1); // single-flight
    expect(useAuthStore.getState().accessToken).toBe("new");
  });

  it("clears the session when the refresh cookie is no longer valid", async () => {
    useAdapter(() => ({ status: 401 }));
    await expect(http.get("/users")).rejects.toBeInstanceOf(AxiosError);
    expect(useAuthStore.getState().status).toBe("anonymous");
    expect(useAuthStore.getState().accessToken).toBeNull();
  });

  it("does not try to refresh after a failed login", async () => {
    const calls = useAdapter(() => ({ status: 401 }));
    await expect(http.post("/auth/login", {})).rejects.toBeInstanceOf(AxiosError);
    expect(calls.map((c) => c.url)).toEqual(["/auth/login"]);
  });

  it("retries the refresh once (another tab may have rotated the cookie)", async () => {
    let attempts = 0;
    useAdapter(() => {
      attempts += 1;
      return attempts === 1 ? { status: 401 } : { status: 200, data: { access_token: "t2" } };
    });
    await expect(refreshAccessToken()).resolves.toBe("t2");
    expect(attempts).toBe(2);
  });
});
