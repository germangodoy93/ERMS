import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AxiosError, AxiosHeaders } from "axios";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";

import { useAuthStore } from "@/stores/auth";
import { makeMe } from "@/test/fixtures";
import type { AgendaOptions, AppointmentRead } from "@/types/api";

import {
  createAppointment,
  getAgendaOptions,
  listAppointments,
  listHolidays,
  updateAppointment,
} from "../api";
import { AgendaPage } from "../pages/AgendaPage";
import { AppointmentFormDialog } from "./AppointmentFormDialog";

vi.mock("../api", () => ({
  getAgendaOptions: vi.fn(),
  listAppointments: vi.fn(),
  listHolidays: vi.fn(),
  createAppointment: vi.fn(),
  updateAppointment: vi.fn(),
  cancelAppointment: vi.fn(),
  getServiceHours: vi.fn(),
  saveServiceHours: vi.fn(),
  listFieldServices: vi.fn(),
  saveFieldService: vi.fn(),
}));

const OPTIONS: AgendaOptions = {
  hours: [
    ...[0, 1, 2, 3, 4].map((weekday) => ({ weekday, opens: "08:00:00", closes: "18:00:00" })),
    { weekday: 5, opens: "08:00:00", closes: "12:00:00" },
    { weekday: 6, opens: null, closes: null },
  ],
  services: [
    {
      id: "s1",
      name: "Visita técnica",
      modality: "ON_SITE",
      duration_minutes: 60,
      price: null,
      tax_rate: 0,
      price_includes_tax: false,
      description: null,
      is_active: true,
    },
  ],
  technicians: [{ id: "t1", full_name: "Técnico Ficticio" }],
  localities: ["Suba", "Kennedy"],
  remote_access_text: "El código de conexión no se guarda en ERMS.",
  can_manage: true,
};

const APPOINTMENT: AppointmentRead = {
  id: "a1",
  number: "CT-2026-000001",
  status: "SCHEDULED",
  modality: "ON_SITE",
  customer: {
    id: "c1",
    full_name: "Ana Ficticia",
    phone: "+573000000001",
    id_type: "CC",
    id_number: "1000000001",
  },
  service: {
    id: "s1",
    name: "Visita técnica",
    price: null,
    tax_rate: 0,
    price_includes_tax: false,
  },
  starts_at: "2026-11-30T14:00:00Z",
  ends_at: "2026-11-30T15:00:00Z",
  duration_minutes: 60,
  technician: { id: "t1", full_name: "Técnico Ficticio" },
  reason: "El computador no enciende.",
  address: "Calle Ficticia 1 # 2-3",
  locality: "Suba",
  notes: null,
  overlap_reason: null,
  remote_consent_channel: null,
  remote_consent_text: null,
  remote_consent_at: null,
  cancel_reason: null,
  cancelled_at: null,
  created_by: { id: "u1", full_name: "Recepcionista Ficticia" },
  created_at: "2026-11-26T15:00:00Z",
};

function wrap(children: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>,
  );
}

function overlapError() {
  const headers = new AxiosHeaders();
  return new AxiosError("409", "ERR_BAD_REQUEST", undefined, undefined, {
    status: 409,
    statusText: "Conflict",
    headers,
    config: { headers },
    data: {
      type: "x",
      title: "El técnico ya tiene otra cita",
      status: 409,
      code: "appointment_overlap",
      detail: "El técnico ya tiene la cita CT-2026-000001 de 09:00 a 10:00.",
      instance: "/api/v1/appointments",
    },
  });
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-11-30T15:00:00Z"));
  useAuthStore.setState({
    status: "authenticated",
    accessToken: "t",
    user: makeMe({ permissions: ["work_orders:read", "appointments:manage"] }),
  });
  vi.mocked(getAgendaOptions).mockResolvedValue(OPTIONS);
  vi.mocked(listHolidays).mockResolvedValue([
    { date: "2026-12-08", name: "Inmaculada Concepción" },
  ]);
  vi.mocked(listAppointments).mockResolvedValue([APPOINTMENT]);
});

afterEach(() => {
  vi.useRealTimers();
});

describe("AgendaPage", () => {
  it("shows the week with hours, appointments and the detail", async () => {
    wrap(<AgendaPage />);
    expect(await screen.findByText("Ana Ficticia")).toBeInTheDocument();
    expect(listAppointments).toHaveBeenCalledWith({
      from: "2026-11-30",
      to: "2026-12-06",
      technicianId: "",
      includeCancelled: false,
    });
    expect(screen.getByText("9:00 – 10:00")).toBeInTheDocument();
    expect(screen.getAllByText("8:00 a 18:00").length).toBeGreaterThan(0);
    expect(screen.getByText("8:00 a 12:00")).toBeInTheDocument();
    // Without service on Sunday and no appointments, Sunday is hidden.
    expect(screen.queryByText(/^Domingo/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByText("Ana Ficticia"));
    expect(await screen.findByText("Cita CT-2026-000001")).toBeInTheDocument();
    expect(screen.getByText("Calle Ficticia 1 # 2-3 · Suba")).toBeInTheDocument();
    expect(screen.getByText("Según el diagnóstico")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mover o editar" })).toBeInTheDocument();
  });

  it("marks holidays and moves to the next week", async () => {
    vi.mocked(listAppointments).mockResolvedValue([]);
    wrap(<AgendaPage />);
    await screen.findAllByText("Sin citas.");
    fireEvent.click(screen.getByRole("button", { name: "Siguiente" }));
    expect(await screen.findByText("Festivo: Inmaculada Concepción")).toBeInTheDocument();
    expect(listAppointments).toHaveBeenLastCalledWith(
      expect.objectContaining({ from: "2026-12-07", to: "2026-12-13" }),
    );
  });

  it("hides scheduling for users who cannot manage the agenda", async () => {
    vi.mocked(getAgendaOptions).mockResolvedValue({ ...OPTIONS, can_manage: false });
    wrap(<AgendaPage />);
    await screen.findByText("Ana Ficticia");
    expect(screen.queryByRole("button", { name: /Nueva cita/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Ana Ficticia"));
    await screen.findByText("Cita CT-2026-000001");
    expect(screen.queryByRole("button", { name: "Mover o editar" })).not.toBeInTheDocument();
  });
});

describe("AppointmentFormDialog", () => {
  it("asks for a reason when the technician is busy and then saves", async () => {
    vi.mocked(updateAppointment)
      .mockRejectedValueOnce(overlapError())
      .mockResolvedValueOnce(APPOINTMENT);
    const onOpenChange = vi.fn();
    wrap(
      <AppointmentFormDialog
        options={OPTIONS}
        open
        onOpenChange={onOpenChange}
        appointment={APPOINTMENT}
      />,
    );
    expect(screen.getByLabelText("Fecha")).toHaveValue("2026-11-30");
    expect(screen.getByLabelText("Hora")).toHaveValue("09:00");
    fireEvent.change(screen.getByLabelText("Hora"), { target: { value: "09:30" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));

    expect(await screen.findByText(/ya tiene la cita CT-2026-000001/)).toBeInTheDocument();
    const force = screen.getByRole("button", { name: "Agendar de todas formas" });
    expect(force).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Razón para agendar de todas formas"), {
      target: { value: "El cliente solo puede a esa hora." },
    });
    fireEvent.click(force);
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
    expect(updateAppointment).toHaveBeenLastCalledWith(
      "a1",
      expect.objectContaining({
        starts_at: "2026-11-30T09:30:00-05:00",
        duration_minutes: 60,
        technician_id: "t1",
        overlap_reason: "El cliente solo puede a esa hora.",
        address: "Calle Ficticia 1 # 2-3",
        locality: "Suba",
      }),
    );
  });

  it("requires the address of an on-site visit", async () => {
    wrap(
      <AppointmentFormDialog
        options={OPTIONS}
        open
        onOpenChange={vi.fn()}
        initialDate="2026-11-30"
      />,
    );
    expect(screen.getByText(/precio según el diagnóstico/)).toBeInTheDocument();
    expect(screen.getByText("Horario: 8:00 a 18:00")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Agendar cita" }));
    expect(await screen.findByText("Indique la dirección.")).toBeInTheDocument();
    expect(screen.getByText("Elija la localidad.")).toBeInTheDocument();
    expect(createAppointment).not.toHaveBeenCalled();
  });
});
