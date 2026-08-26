import { useState } from "react";
import { useBudget, useUpdateBudget } from "../../hooks/useStats";
import { formatMonth, getCurrentMonth } from "../../lib/format";
import { ErrorMessage } from "../common/ErrorMessage";
import { LoadingSpinner } from "../common/LoadingSpinner";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { BudgetStatusCard } from "./BudgetStatusCard";

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
    return <ErrorMessage message="Budgetstatus konnte nicht geladen werden." onRetry={refetch} />;
  }

  const isOverBudget = data.remaining_cents < 0;

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
      setValidationError("Bitte gib ein Budget von 0 oder mehr ein.");
      return;
    }

    updateBudget.mutate(
      { monthly_budget_cents: Math.round(draftEuros * 100) },
      { onSuccess: () => setIsEditing(false) },
    );
  };

  if (isEditing) {
    return (
      <Card
        testId="budget-widget"
        data-state={isOverBudget ? "over" : "within"}
        className={isOverBudget ? "bg-negative-50" : "bg-positive-50"}
      >
        <p className="text-sm font-medium text-gray-700">Budget für {formatMonth(data.month)}</p>
        <div className="mt-3">
          <label className="block text-sm font-medium text-gray-700" htmlFor="monthly-budget-input">
            Monatsbudget (€)
          </label>
          <input
            id="monthly-budget-input"
            type="number"
            min="0"
            step="0.01"
            value={draftValue}
            onChange={(event) => setDraftValue(event.target.value)}
            className="mt-1 w-40 rounded-lg border border-surface-border bg-surface px-3 py-1.5 text-gray-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          />
          {validationError && (
            <p className="mt-1 text-sm font-medium text-negative-700">{validationError}</p>
          )}
          <div className="mt-3 flex gap-2">
            <Button onClick={saveBudget}>Speichern</Button>
            <Button variant="secondary" onClick={cancelEditing}>
              Abbrechen
            </Button>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <BudgetStatusCard
      data={data}
      testId="budget-widget"
      action={
        <Button variant="ghost" onClick={startEditing}>
          Budget bearbeiten
        </Button>
      }
    />
  );
}
