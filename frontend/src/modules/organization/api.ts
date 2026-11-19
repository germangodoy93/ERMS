import { http } from "@/services/http";
import type {
  CurrentPrivacyPolicy,
  Organization,
  OrganizationUpdate,
  PrivacyPolicy,
  PrivacyPolicyDraft,
  PrivacyPolicyVersion,
} from "@/types/api";

export async function getOrganization(): Promise<Organization> {
  const { data } = await http.get<Organization>("/organization");
  return data;
}

export async function updateOrganization(payload: OrganizationUpdate): Promise<Organization> {
  const { data } = await http.patch<Organization>("/organization", payload);
  return data;
}

export async function getCurrentPolicy(): Promise<CurrentPrivacyPolicy> {
  const { data } = await http.get<CurrentPrivacyPolicy>("/privacy-policy");
  return data;
}

export async function getPolicyDraft(): Promise<PrivacyPolicyDraft> {
  const { data } = await http.get<PrivacyPolicyDraft>("/privacy-policy/draft");
  return data;
}

export async function listPolicyVersions(): Promise<PrivacyPolicyVersion[]> {
  const { data } = await http.get<PrivacyPolicyVersion[]>("/privacy-policy/versions");
  return data;
}

export async function getPolicyVersion(version: number): Promise<PrivacyPolicy> {
  const { data } = await http.get<PrivacyPolicy>(`/privacy-policy/versions/${version}`);
  return data;
}

export async function publishPolicy(content: string): Promise<PrivacyPolicy> {
  const { data } = await http.post<PrivacyPolicy>("/privacy-policy", { content });
  return data;
}
