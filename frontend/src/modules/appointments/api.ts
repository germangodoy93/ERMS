import { http } from "@/services/http";
import type {
  AgendaOptions,
  AppointmentCreate,
  AppointmentRead,
  AppointmentUpdate,
  FieldService,
  FieldServiceWrite,
  Holiday,
  HoursDay,
  HoursRead,
} from "@/types/api";

export interface AgendaRange {
  from: string;
  to: string;
  technicianId?: string;
  includeCancelled?: boolean;
}

export async function getAgendaOptions(): Promise<AgendaOptions> {
  return (await http.get<AgendaOptions>("/appointments/options")).data;
}

export async function listAppointments(range: AgendaRange): Promise<AppointmentRead[]> {
  const params = {
    from: range.from,
    to: range.to,
    technician_id: range.technicianId || undefined,
    include_cancelled: range.includeCancelled || undefined,
  };
  return (await http.get<AppointmentRead[]>("/appointments", { params })).data;
}

export async function listHolidays(from: string, to: string): Promise<Holiday[]> {
  return (await http.get<Holiday[]>("/appointments/holidays", { params: { from, to } })).data;
}

export async function createAppointment(data: AppointmentCreate): Promise<AppointmentRead> {
  return (await http.post<AppointmentRead>("/appointments", data)).data;
}

export async function updateAppointment(
  id: string,
  data: AppointmentUpdate,
): Promise<AppointmentRead> {
  return (await http.patch<AppointmentRead>(`/appointments/${id}`, data)).data;
}

export async function cancelAppointment(id: string, reason: string): Promise<AppointmentRead> {
  return (await http.post<AppointmentRead>(`/appointments/${id}/cancel`, { reason })).data;
}

export async function getServiceHours(): Promise<HoursRead> {
  return (await http.get<HoursRead>("/appointments/hours")).data;
}

export async function saveServiceHours(days: HoursDay[]): Promise<HoursRead> {
  return (await http.put<HoursRead>("/appointments/hours", { days })).data;
}

export async function listFieldServices(): Promise<FieldService[]> {
  return (await http.get<FieldService[]>("/appointments/services")).data;
}

export async function saveFieldService(
  id: string | null,
  data: FieldServiceWrite,
): Promise<FieldService> {
  return id
    ? (await http.put<FieldService>(`/appointments/services/${id}`, data)).data
    : (await http.post<FieldService>("/appointments/services", data)).data;
}
