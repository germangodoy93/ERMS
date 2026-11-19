import "@testing-library/jest-dom/vitest";

// jsdom does not implement ResizeObserver, used by Radix UI primitives (checkbox, select).
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub;
