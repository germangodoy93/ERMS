import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";

import { useAuthStore } from "@/stores/auth";
import { makeMe } from "@/test/fixtures";
import type { NoticePanel, NoticeRead, PendingNotice } from "@/types/api";

import { getNoticePanel, getPendingNotices, prepareNotice } from "../api";
import { OrderNoticesCard } from "./OrderNoticesCard";
import { PendingNoticesCard } from "./PendingNoticesCard";

vi.mock("../api", () => ({
  getNoticePanel: vi.fn(),
  prepareNotice: vi.fn(),
  getPendingNotices: vi.fn(),
}));

const RECEIVED: NoticeRead = {
  id: "n1",
  kind: "RECEIVED",
  label: "Orden recibida",
  phone: "+573000000001",
  body: "Hola Ana, recibimos su equipo.",
  prepared_by: { id: "u1", full_name: "Recepcionista Ficticia" },
  prepared_at: "2026-11-20T15:00:00Z",
};

const PANEL: NoticePanel = {
  phone: "+573000000001",
  can_whatsapp: true,
  blocked_reason: null,
  can_prepare: true,
  suggested: "READY",
  pending: true,
  drafts: [
    { kind: "RECEIVED", label: "Orden recibida", body: "Hola Ana, recibimos su equipo." },
    { kind: "READY", label: "Equipo listo", body: "Hola Ana, su equipo está listo." },
    { kind: "FREE", label: "Mensaje libre", body: "Hola Ana, " },
  ],
  history: [RECEIVED],
};

function wrap(children: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("OrderNoticesCard", () => {
  it("suggests the pending notice and prepares it with the edited text", async () => {
    vi.mocked(getNoticePanel).mockResolvedValue(PANEL);
    const url = "https://wa.me/573000000001?text=Hola%20Ana";
    vi.mocked(prepareNotice).mockResolvedValue({
      notice: { ...RECEIVED, kind: "READY" },
      url,
    });
    wrap(<OrderNoticesCard orderId="o1" />);

    expect(await screen.findByText("Aviso pendiente:")).toBeInTheDocument();
    expect(screen.getByText(/por Recepcionista Ficticia/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Avisar por WhatsApp/ }));
    const message = screen.getByLabelText("Mensaje");
    expect(message).toHaveValue("Hola Ana, su equipo está listo.");
    expect(screen.getByText("300 000 0001", { exact: false })).toBeInTheDocument();
    fireEvent.change(message, { target: { value: "Hola Ana, ya puede recogerlo." } });
    fireEvent.click(screen.getByRole("button", { name: /Preparar mensaje/ }));

    await waitFor(() =>
      expect(prepareNotice).toHaveBeenCalledWith("o1", "READY", "Hola Ana, ya puede recogerlo."),
    );
    expect(await screen.findByRole("link", { name: /Abrir WhatsApp aquí/ })).toHaveAttribute(
      "href",
      url,
    );
    const qr = await screen.findByAltText("Código QR para abrir el chat en el celular");
    expect(qr.getAttribute("src")).toMatch(/^data:image\/svg\+xml/);
  });

  it("explains why WhatsApp is not available", async () => {
    vi.mocked(getNoticePanel).mockResolvedValue({
      ...PANEL,
      phone: "+576015551234",
      can_whatsapp: false,
      blocked_reason: "El teléfono del cliente es fijo; WhatsApp necesita un celular.",
      history: [],
    });
    wrap(<OrderNoticesCard orderId="o1" />);
    expect(await screen.findByText(/es fijo/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Avisar por WhatsApp/ })).toBeDisabled();
    expect(screen.getByText("Todavía no hay avisos.")).toBeInTheDocument();
  });

  it("hides the button for users who cannot notify", async () => {
    vi.mocked(getNoticePanel).mockResolvedValue({ ...PANEL, can_prepare: false });
    wrap(<OrderNoticesCard orderId="o1" />);
    expect(await screen.findByText("Aviso pendiente:")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Avisar por WhatsApp/ })).not.toBeInTheDocument();
  });
});

describe("PendingNoticesCard", () => {
  const pending: PendingNotice[] = [
    {
      work_order_id: "o1",
      number: "ER-2026-000123",
      customer_name: "Ana Ficticia",
      status: "LISTO_ENTREGA",
      kind: "REMINDER",
      label: "Recordatorio: equipo sin retirar",
      since: "2026-11-18T15:00:00Z",
      can_whatsapp: false,
    },
  ];

  it("lists orders to notify for users with the permission", async () => {
    useAuthStore.setState({
      status: "authenticated",
      accessToken: "t",
      user: makeMe({ permissions: ["customers:notify"] }),
    });
    vi.mocked(getPendingNotices).mockResolvedValue(pending);
    wrap(<PendingNoticesCard />);
    expect(await screen.findByText("ER-2026-000123")).toBeInTheDocument();
    expect(screen.getByText("Recordatorio: equipo sin retirar")).toBeInTheDocument();
    expect(screen.getByText("(sin celular: llamar)")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /ER-2026-000123/ })).toHaveAttribute(
      "href",
      "/ordenes/o1",
    );
  });

  it("is hidden without the permission", () => {
    useAuthStore.setState({ status: "authenticated", accessToken: "t", user: makeMe() });
    const { container } = wrap(<PendingNoticesCard />);
    expect(container).toBeEmptyDOMElement();
    expect(getPendingNotices).not.toHaveBeenCalled();
  });
});
