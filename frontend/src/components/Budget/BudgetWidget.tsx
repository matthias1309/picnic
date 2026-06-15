import { useState } from "react";
import { useBudget, useUpdateBudget } from "../../hooks/useStats";
import { formatCents, getCurrentMonth } from "../../lib/format";
import { ErrorMessage } from "../common/ErrorMessage";
import { LoadingSpinner } from "../common/LoadingSpinner";

export function BudgetWidget() {
  const month = getCurrentMonth();
  const { data, isLoading, isError, refetch } = useBudget(month);
  const updateBudget = useUpdateBudget();
  const [isEditing, setIsEditing] = useState(false);
  const [draftValue, setDraftValue] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (isError || !data) {
    return <ErrorMessage message="Failed to load budget status." onRetry={refetch} />;
  }

  const isOverBudget = data.remaining_cents < 0;
  const percentSpent = data.budget_cents > 0 ? (data.spent_cents / data.budget_cents) * 100 : 0;

  const startEditing = () => {
    setDraftValue((data.budget_cents / 100).toString());
    setValidationError(null);
    setIsEditing(true);
  };

  const cancelEditing = () => {
    setIsEditing(false);
    setValidationError(null);
  };

  const saveBudget = () => {
    const draftEuros = Number(draftValue);
    if (!Number.isFinite(draftEuros) || draftEuros < 0) {
      setValidationError("Please enter a budget of 0 or more.");
      return;
    }

    updateBudget.mutate(
      { monthly_budget_cents: Math.round(draftEuros * 100) },
      { onSuccess: () => setIsEditing(false) },
    );
  };

  return (
    <div
      data-testid="budget-widget"
      className={`rounded-lg p-4 shadow ${isOverBudget ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"}`}
    >
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">Budget for {data.month}</p>
        {!isEditing && (
          <button type="button" onClick={startEditing} className="text-sm font-medium underline">
            Edit budget
          </button>
        )}
      </div>
      {isEditing ? (
        <div className="mt-2">
          <label className="block text-sm font-medium" htmlFor="monthly-budget-input">
            Monthly budget (€)
          </label>
          <input
            id="monthly-budget-input"
            type="number"
            min="0"
            step="0.01"
            value={draftValue}
            onChange={(event) => setDraftValue(event.target.value)}
            className="mt-1 rounded border border-gray-300 px-2 py-1 text-gray-900"
          />
          {validationError && <p className="mt-1 text-sm font-medium">{validationError}</p>}
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              onClick={saveBudget}
              className="rounded bg-gray-800 px-3 py-1 text-sm font-medium text-white"
            >
              Save
            </button>
            <button
              type="button"
              onClick={cancelEditing}
              className="rounded border border-gray-300 px-3 py-1 text-sm font-medium"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <>
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
        </>
      )}
    </div>
  );
}
