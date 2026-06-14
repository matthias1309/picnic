import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { BudgetWidget } from "../src/components/Budget/BudgetWidget";
import * as apiClient from "../src/api/client";
import { renderWithProviders } from "./test-utils";
import type { BudgetStatus } from "../src/types";

const UNDER_BUDGET_FIXTURE: BudgetStatus = {
  month: "2026-06",
  budget_cents: 30000,
  spent_cents: 12000,
  remaining_cents: 18000,
};

const OVER_BUDGET_FIXTURE: BudgetStatus = {
  month: "2026-06",
  budget_cents: 30000,
  spent_cents: 35000,
  remaining_cents: -5000,
};

describe("BudgetWidget", () => {
  // TC-005-05
  // Given a budget is configured in the backend
  // When the user views the budget widget
  // Then actual spend versus budget for the current month is displayed
  // And an over-budget state is visually distinct
  it("displays spend versus budget for the current month", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockResolvedValue(UNDER_BUDGET_FIXTURE);

    // Act
    renderWithProviders(<BudgetWidget />);

    // Assert
    const widget = await screen.findByTestId("budget-widget");
    expect(widget).toHaveTextContent("120,00 €");
    expect(widget).toHaveTextContent("300,00 €");
  });

  it("applies a distinct visual style when over budget", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockResolvedValue(UNDER_BUDGET_FIXTURE);

    // Act
    renderWithProviders(<BudgetWidget />);

    // Assert
    const widget = await screen.findByTestId("budget-widget");
    expect(widget.className).not.toContain("red");
  });

  it("shows the over-budget state distinctly when spend exceeds the budget", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockResolvedValue(OVER_BUDGET_FIXTURE);

    // Act
    renderWithProviders(<BudgetWidget />);

    // Assert
    const widget = await screen.findByTestId("budget-widget");
    expect(widget.className).toContain("red");
    expect(widget).toHaveTextContent("350,00 €");
    expect(widget).toHaveTextContent("Over budget");
  });
});
