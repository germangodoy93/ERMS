import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { reloadCurrentUser } from "@/modules/auth/session";
import type { OrganizationUpdate } from "@/types/api";

import {
  getCurrentPolicy,
  getOrganization,
  getPolicyDraft,
  getPolicyVersion,
  publishPolicy,
  updateOrganization,
} from "./api";

export const organizationKey = ["organization"] as const;
export const policyKeys = {
  all: ["privacy-policy"] as const,
  current: ["privacy-policy", "current"] as const,
  draft: ["privacy-policy", "draft"] as const,
  version: (version: number) => ["privacy-policy", "version", version] as const,
};

export function useOrganization() {
  return useQuery({ queryKey: organizationKey, queryFn: getOrganization });
}

export function useUpdateOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OrganizationUpdate) => updateOrganization(payload),
    onSuccess: async (organization) => {
      queryClient.setQueryData(organizationKey, organization);
      await queryClient.invalidateQueries({ queryKey: policyKeys.draft });
      await reloadCurrentUser(); // the header shows the workshop name
    },
  });
}

/** Policy in force and the authorization texts shown at reception. */
export function useCurrentPolicy() {
  return useQuery({ queryKey: policyKeys.current, queryFn: getCurrentPolicy, staleTime: 60_000 });
}

export function usePolicyDraft(enabled: boolean) {
  return useQuery({ queryKey: policyKeys.draft, queryFn: getPolicyDraft, enabled });
}

export function usePolicyVersion(version: number | null) {
  return useQuery({
    queryKey: policyKeys.version(version ?? 0),
    queryFn: () => getPolicyVersion(version ?? 0),
    enabled: version !== null,
    staleTime: Infinity, // published versions never change
  });
}

export function usePublishPolicy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (content: string) => publishPolicy(content),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: policyKeys.all }),
  });
}
