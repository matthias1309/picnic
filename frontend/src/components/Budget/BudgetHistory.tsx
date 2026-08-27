import { useQueries } from "@tanstack/react-query";
import { fetchJson } from "../../api/client";
import { formatMonth, getPastMonths } from "../../lib/format";
import type { BudgetStatus } from "../../types";
import { Card } from "../ui/Card";
import { SectionHeader } from "../ui/SectionHeader";
import { BudgetStatusCard } from "./BudgetStatusCard";

const HISTORY_MONTHS = 12;

export function BudgetHistory() {
  const months = getPastMonths(HISTORY_MONTHS);

  const results = useQueries({
    queries: months.map((month) => ({
      queryKey: ["stats", "budget", month],
      queryFn: () => fetchJson<BudgetStatus>("/stats/budget", { month }),
    })),
  });

  return (
    <Card>
      <SectionHeader title="Frühere Monate" />
      <div className="divide-y divide-surface-border">
        {results.map((result, index) => {
          const month = months[index];

          if (result.isLoading) {
            return null;
          }

          if (result.isError || !result.data) {
            return (
              <p key={month} className="py-3 text-sm text-negative-700">
                Budget für {formatMonth(month)} konnte nicht geladen werden.
              </p>
            );
          }

          return (
            <BudgetStatusCard key={month} data={result.data} testId="budget-history-card" compact />
          );
        })}
      </div>
    </Card>
  );
}
