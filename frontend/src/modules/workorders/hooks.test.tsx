import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";

import type { WorkOrder } from "@/types/api";

import { changeStatus } from "./api";
import { useChangeStatus, workOrderKeys } from "./hooks";

vi.mock("./api", () => ({ changeStatus: vi.fn() }));

describe("useChangeStatus", () => {
  it("refreshes the order panels, lists and dashboard, not other orders", async () => {
    const client = new QueryClient();
    const order = { id: "o1", status: "DIAGNOSTICO" } as WorkOrder;
    vi.mocked(changeStatus).mockResolvedValue(order);
    for (const key of [
      ["work-orders", "diagnostic", "o1"],
      ["work-orders", "billing", "o1"],
      ["work-orders", "diagnostic", "o2"],
      ["work-orders", "list", {}],
      ["dashboard"],
    ]) {
      client.setQueryData(key, {});
    }
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(() => useChangeStatus(), { wrapper });

    await act(() => result.current.mutateAsync({ id: "o1", status: "DIAGNOSTICO", reason: null }));

    const stale = (key: unknown[]) => client.getQueryState(key)?.isInvalidated;
    expect(stale(["work-orders", "diagnostic", "o1"])).toBe(true);
    expect(stale(["work-orders", "billing", "o1"])).toBe(true);
    expect(stale(["work-orders", "list", {}])).toBe(true);
    expect(stale(["dashboard"])).toBe(true);
    expect(stale(["work-orders", "diagnostic", "o2"])).toBe(false);
    expect(client.getQueryData(workOrderKeys.detail("o1"))).toEqual(order);
  });
});
