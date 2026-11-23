import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  AssemblyChecklist,
  BuildWrite,
  CatalogImportItem,
  EvaluateRequest,
} from "@/types/api";

import {
  completeStep,
  consumeParts,
  deleteBuild,
  evaluateBuild,
  getBuild,
  getCatalog,
  getChecklist,
  importCatalog,
  uploadCosts,
  listBuilds,
  orderBuild,
  saveBuild,
} from "./api";

export const assemblyKeys = {
  catalog: ["assembly", "catalog"] as const,
  builds: ["assembly", "builds"] as const,
  build: (id: string) => ["assembly", "build", id] as const,
  evaluation: (req: EvaluateRequest) => ["assembly", "evaluate", req] as const,
  checklist: (orderId: string) => ["work-orders", "assembly", orderId] as const,
};

export function useCatalog() {
  return useQuery({ queryKey: assemblyKeys.catalog, queryFn: getCatalog, staleTime: 60_000 });
}

export function useEvaluation(request: EvaluateRequest) {
  return useQuery({
    queryKey: assemblyKeys.evaluation(request),
    queryFn: () => evaluateBuild(request),
    placeholderData: keepPreviousData,
  });
}

export function useBuilds() {
  return useQuery({ queryKey: assemblyKeys.builds, queryFn: listBuilds });
}

export function useBuild(id: string | undefined) {
  return useQuery({
    queryKey: assemblyKeys.build(id ?? ""),
    queryFn: () => getBuild(id ?? ""),
    enabled: Boolean(id),
  });
}

export function useSaveBuild() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ payload, id }: { payload: BuildWrite; id?: string }) => saveBuild(payload, id),
    onSuccess: (build) => {
      queryClient.setQueryData(assemblyKeys.build(build.id), build);
      return queryClient.invalidateQueries({ queryKey: assemblyKeys.builds });
    },
  });
}

export function useDeleteBuild() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteBuild,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: assemblyKeys.builds }),
  });
}

export function useOrderBuild() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, customerId }: { id: string; customerId: string }) =>
      orderBuild(id, customerId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["assembly"] }),
  });
}

export function useImportCatalog() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (items: CatalogImportItem[]) => importCatalog(items),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ["assembly"] }),
        queryClient.invalidateQueries({ queryKey: ["inventory"] }),
      ]),
  });
}

export function useUploadCosts() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadCosts(file),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ["assembly"] }),
        queryClient.invalidateQueries({ queryKey: ["inventory"] }),
      ]),
  });
}

export function useChecklist(orderId: string) {
  return useQuery({
    queryKey: assemblyKeys.checklist(orderId),
    queryFn: () => getChecklist(orderId),
  });
}

/** Checklist actions also change the order's repair tasks and the stock. */
export function useChecklistActions(orderId: string) {
  const queryClient = useQueryClient();
  const onSuccess = async (checklist: AssemblyChecklist) => {
    queryClient.setQueryData(assemblyKeys.checklist(orderId), checklist);
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["work-orders", "repair", orderId] }),
      queryClient.invalidateQueries({ queryKey: ["inventory"] }),
      queryClient.invalidateQueries({ queryKey: assemblyKeys.catalog }),
    ]);
  };
  return {
    consume: useMutation({ mutationFn: () => consumeParts(orderId), onSuccess }),
    step: useMutation({ mutationFn: (code: string) => completeStep(orderId, code), onSuccess }),
  };
}
