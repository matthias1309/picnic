import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchJson, putJson } from "../api/client";
import type {
  BudgetSettingOut,
  BudgetSettingUpdate,
  BudgetStatus,
  CategoryKey,
  CategorySpending,
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

export function useSpending(granularity: SpendingGranularity, category?: CategoryKey) {
  return useQuery({
    queryKey: ["stats", "spending", granularity, category],
    queryFn: () => fetchJson<SpendingOverTime>("/stats/spending", { granularity, category }),
  });
}

export function useTopItems(limit: number = 10, category?: CategoryKey) {
  return useQuery({
    queryKey: ["stats", "top-items", limit, category],
    queryFn: () => fetchJson<TopItem[]>("/stats/top-items", { limit, category }),
  });
}

export function useSpendingByCategory(fromDate?: string, toDate?: string) {
  return useQuery({
    queryKey: ["stats", "by-category", fromDate, toDate],
    queryFn: () =>
      fetchJson<CategorySpending[]>("/stats/by-category", {
        from_date: fromDate,
        to_date: toDate,
      }),
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
