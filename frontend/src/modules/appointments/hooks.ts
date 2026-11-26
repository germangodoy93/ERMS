import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  AppointmentCreate,
  AppointmentUpdate,
  FieldServiceWrite,
  HoursDay,
} from "@/types/api";

import {
  cancelAppointment,
  createAppointment,
  getAgendaOptions,
  getServiceHours,
  listAppointments,
  listFieldServices,
  listHolidays,
  saveFieldService,
  saveServiceHours,
  updateAppointment,
  type AgendaRange,
} from "./api";

export const agendaKeys = {
  all: ["agenda"] as const,
  options: ["agenda", "options"] as const,
  list: (range: AgendaRange) => ["agenda", "list", range] as const,
  holidays: (from: string, to: string) => ["agenda", "holidays", from, to] as const,
  hours: ["agenda", "hours"] as const,
  services: ["agenda", "services"] as const,
};

export function useAgendaOptions() {
  return useQuery({ queryKey: agendaKeys.options, queryFn: getAgendaOptions });
}

export function useAppointments(range: AgendaRange) {
  return useQuery({ queryKey: agendaKeys.list(range), queryFn: () => listAppointments(range) });
}

export function useHolidays(from: string, to: string) {
  return useQuery({
    queryKey: agendaKeys.holidays(from, to),
    queryFn: () => listHolidays(from, to),
    staleTime: Infinity,
  });
}

/** Every change to the agenda refreshes lists, options and settings. */
function useAgendaMutation<T, R>(fn: (args: T) => Promise<R>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: agendaKeys.all }),
  });
}

export function useCreateAppointment() {
  return useAgendaMutation((data: AppointmentCreate) => createAppointment(data));
}

export function useUpdateAppointment() {
  return useAgendaMutation(({ id, data }: { id: string; data: AppointmentUpdate }) =>
    updateAppointment(id, data),
  );
}

export function useCancelAppointment() {
  return useAgendaMutation(({ id, reason }: { id: string; reason: string }) =>
    cancelAppointment(id, reason),
  );
}

export function useServiceHours() {
  return useQuery({ queryKey: agendaKeys.hours, queryFn: getServiceHours });
}

export function useSaveServiceHours() {
  return useAgendaMutation((days: HoursDay[]) => saveServiceHours(days));
}

export function useFieldServices() {
  return useQuery({ queryKey: agendaKeys.services, queryFn: listFieldServices });
}

export function useSaveFieldService() {
  return useAgendaMutation(({ id, data }: { id: string | null; data: FieldServiceWrite }) =>
    saveFieldService(id, data),
  );
}
