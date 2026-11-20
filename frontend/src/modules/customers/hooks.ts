import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  ConsentChange,
  ConsentChannel,
  Customer,
  CustomerCreate,
  CustomerUpdate,
} from "@/types/api";

import {
  anonymizeCustomer,
  changeConsent,
  createCustomer,
  getCustomer,
  listConsents,
  listCustomers,
  updateCustomer,
  type CustomerFilters,
} from "./api";

export const customerKeys = {
  all: ["customers"] as const,
  list: (filters: CustomerFilters) => ["customers", "list", filters] as const,
  detail: (id: string) => ["customers", "detail", id] as const,
  consents: (id: string) => ["customers", "consents", id] as const,
};

export function useCustomers(filters: CustomerFilters) {
  return useQuery({
    queryKey: customerKeys.list(filters),
    queryFn: () => listCustomers(filters),
    placeholderData: keepPreviousData,
  });
}

export function useCustomer(id: string) {
  return useQuery({
    queryKey: customerKeys.detail(id),
    queryFn: () => getCustomer(id),
    enabled: Boolean(id),
  });
}

export function useConsentHistory(id: string) {
  return useQuery({ queryKey: customerKeys.consents(id), queryFn: () => listConsents(id) });
}

/** After any change: refresh lists and store the returned customer as the detail. */
function useOnCustomerSaved() {
  const queryClient = useQueryClient();
  return async (customer: Customer) => {
    queryClient.setQueryData(customerKeys.detail(customer.id), customer);
    await queryClient.invalidateQueries({ queryKey: customerKeys.all });
  };
}

export function useCreateCustomer() {
  const onSaved = useOnCustomerSaved();
  return useMutation({
    mutationFn: (payload: CustomerCreate) => createCustomer(payload),
    onSuccess: onSaved,
  });
}

export function useUpdateCustomer() {
  const onSaved = useOnCustomerSaved();
  return useMutation({
    mutationFn: ({ id, changes }: { id: string; changes: CustomerUpdate }) =>
      updateCustomer(id, changes),
    onSuccess: onSaved,
  });
}

export function useChangeConsent() {
  const onSaved = useOnCustomerSaved();
  return useMutation({
    mutationFn: ({ id, change }: { id: string; change: ConsentChange }) =>
      changeConsent(id, change),
    onSuccess: onSaved,
  });
}

export function useAnonymizeCustomer() {
  const onSaved = useOnCustomerSaved();
  return useMutation({
    mutationFn: ({ id, channel }: { id: string; channel: ConsentChannel }) =>
      anonymizeCustomer(id, channel),
    onSuccess: onSaved,
  });
}
