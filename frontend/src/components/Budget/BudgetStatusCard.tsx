import type { ReactNode } from "react";
import { formatCents } from "../../lib/format";
import type { BudgetStatus } from "../../types";

interface BudgetStatusCardProps {
  data: BudgetStatus;
  action?: ReactNode;
  testId?: string;
}

export function BudgetStatusCard({
  data,
  action,
  testId = "budget-widget",
}: BudgetStatusCardProps) {
  const isOverBudget = data.remaining_cents < 0;
  const percentSpent = data.budget_cents > 0 ? (data.spent_cents / data.budget_cents) * 100 : 0;

  return (
    <div
      data-testid={testId}
      className={`rounded-lg p-4 shadow ${isOverBudget ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"}`}
    >
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">Budget for {data.month}</p>
        {action}
      </div>
      <p className="text-xl font-semibold">
        {formatCents(data.spent_cents)} / {formatCents(data.budget_cents)}
      </p>
      <div className="mt-2 h-2 w-full rounded bg-gray-200">
        <div
          className={`h-2 rounded ${isOverBudget ? "bg-red-600" : "bg-green-600"}`}
          style={{ width: `${Math.min(percentSpent, 100)}%` }}
        />
      </div>
      {isOverBudget ? (
        <p className="mt-2 text-sm font-medium">
          Over budget by {formatCents(-data.remaining_cents)}
        </p>
      ) : (
        <p className="mt-2 text-sm">Remaining: {formatCents(data.remaining_cents)}</p>
      )}
    </div>
  );
}
