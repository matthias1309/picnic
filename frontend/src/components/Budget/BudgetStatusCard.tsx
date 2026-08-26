import type { ReactNode } from "react";
import { formatCents, formatMonth } from "../../lib/format";
import type { BudgetStatus } from "../../types";
import { Card } from "../ui/Card";

interface BudgetStatusCardProps {
  data: BudgetStatus;
  action?: ReactNode;
  testId?: string;
  /** Single-row rendering for the history list, where twelve full cards would be a wall. */
  compact?: boolean;
}

export function BudgetStatusCard({
  data,
  action,
  testId = "budget-widget",
  compact = false,
}: BudgetStatusCardProps) {
  const isOverBudget = data.remaining_cents < 0;
  const percentSpent = data.budget_cents > 0 ? (data.spent_cents / data.budget_cents) * 100 : 0;
  const barColor = isOverBudget ? "bg-negative-600" : "bg-positive-600";

  if (compact) {
    return (
      <div
        data-testid={testId}
        data-state={isOverBudget ? "over" : "within"}
        className="grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-1 py-3"
      >
        <span className="text-sm font-medium text-gray-700">{formatMonth(data.month)}</span>
        <span className="text-sm tabular-nums text-gray-600">
          {formatCents(data.spent_cents)} / {formatCents(data.budget_cents)}
        </span>
        <div className="col-span-2 h-1.5 w-full rounded-full bg-surface-muted">
          <div
            className={`h-1.5 rounded-full ${barColor}`}
            style={{ width: `${Math.min(percentSpent, 100)}%` }}
          />
        </div>
        <span
          className={`col-span-2 text-xs ${isOverBudget ? "text-negative-700" : "text-gray-500"}`}
        >
          {isOverBudget
            ? `${formatCents(-data.remaining_cents)} über Budget`
            : `Verbleibend: ${formatCents(data.remaining_cents)}`}
        </span>
      </div>
    );
  }

  return (
    <Card
      testId={testId}
      data-state={isOverBudget ? "over" : "within"}
      className={
        isOverBudget ? "bg-negative-50 text-negative-700" : "bg-positive-50 text-positive-700"
      }
    >
      <div>
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm font-medium">Budget für {formatMonth(data.month)}</p>
          {action}
        </div>
        <p className="mt-1 text-2xl font-semibold tabular-nums">
          {formatCents(data.spent_cents)} / {formatCents(data.budget_cents)}
        </p>
        <div className="mt-3 h-2 w-full rounded-full bg-white/60">
          <div
            className={`h-2 rounded-full ${barColor}`}
            style={{ width: `${Math.min(percentSpent, 100)}%` }}
          />
        </div>
        {isOverBudget ? (
          <p className="mt-2 text-sm font-medium">
            {formatCents(-data.remaining_cents)} über Budget
          </p>
        ) : (
          <p className="mt-2 text-sm">Verbleibend: {formatCents(data.remaining_cents)}</p>
        )}
      </div>
    </Card>
  );
}
