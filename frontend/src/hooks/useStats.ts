import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchJson, putJson } from "../api/client";
import type {
  BudgetSettingOut,
  BudgetSettingUpdate,
  BudgetStatus,
  PriceTrend,
  SpendingGranularity,
  SpendingOverTime,
  SummaryStats,
  TopItem,
} from "../types";

export function useSummary() {
  return useQuery({
    queryKey: ["stats", "summary"],
    queryFn: () => fetchJson<SummaryStats>("/stats/summary"),
  });
}

export function useBudget(month: string) {
  return useQuery({
    queryKey: ["stats", "budget", month],
    queryFn: () => fetchJson<BudgetStatus>("/stats/budget", { month }),
  });
}

export function useUpdateBudget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: BudgetSettingUpdate) =>
      putJson<BudgetSettingOut>("/settings/budget", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stats", "budget"] });
    },
  });
}

export function useSpending(granularity: SpendingGranularity) {
  return useQuery({
    queryKey: ["stats", "spending", granularity],
    queryFn: () => fetchJson<SpendingOverTime>("/stats/spending", { granularity }),
  });
}

export function useTopItems(limit: number = 10) {
  return useQuery({
    queryKey: ["stats", "top-items", limit],
    queryFn: () => fetchJson<TopItem[]>("/stats/top-items", { limit }),
  });
}

export function usePriceTrend(productId: number | null, fromDate?: string) {
  return useQuery({
    queryKey: ["stats", "price-trend", productId, fromDate],
    queryFn: () =>
      fetchJson<PriceTrend>(`/stats/price-trend/${productId}`, { from_date: fromDate }),
    enabled: productId !== null,
  });
}
