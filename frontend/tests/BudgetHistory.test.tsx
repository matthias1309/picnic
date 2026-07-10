import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { BudgetHistory } from "../src/components/Budget/BudgetHistory";
import { BudgetWidget } from "../src/components/Budget/BudgetWidget";
import * as apiClient from "../src/api/client";
import { renderWithProviders } from "./test-utils";
import type { BudgetStatus } from "../src/types";

function budgetFor(month: string, overrides: Partial<BudgetStatus> = {}): BudgetStatus {
  return {
    month,
    budget_cents: 30000,
    spent_cents: 12000,
    remaining_cents: 18000,
    ...overrides,
  };
}

describe("BudgetHistory", () => {
  // TC-017-02
  // Given the API returns a budget status for each of the last 12 months
  // When the user views the BudgetHistory component
  // Then 12 budget cards are rendered, one for each preceding month
  // And none of them shows an "Edit budget" control
  it("renders one read-only card per historical month", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockImplementation((_path, params) =>
      Promise.resolve(budgetFor(String(params?.month))),
    );

    // Act
    renderWithProviders(<BudgetHistory />);

    // Assert
    const cards = await screen.findAllByTestId("budget-history-card");
    expect(cards).toHaveLength(12);
    expect(screen.queryByRole("button", { name: /edit budget/i })).not.toBeInTheDocument();
  });

  // TC-017-03
  // Given a historical month's spend exceeds its budget
  // When its card is rendered
  // Then the card shows the over-budget color and "Over budget by" text
  it("shows the over-budget style for a month that exceeded its budget", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockImplementation((_path, params) =>
      Promise.resolve(
        budgetFor(String(params?.month), { spent_cents: 35000, remaining_cents: -5000 }),
      ),
    );

    // Act
    renderWithProviders(<BudgetHistory />);

    // Assert
    const cards = await screen.findAllByTestId("budget-history-card");
    expect(cards[0].className).toContain("red");
    expect(cards[0]).toHaveTextContent("Over budget by");
  });

  // TC-017-04
  // Given a historical month's spend is within budget
  // When its card is rendered
  // Then the card shows the under-budget color and "Remaining" text
  it("shows the under-budget style for a month within budget", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockImplementation((_path, params) =>
      Promise.resolve(budgetFor(String(params?.month))),
    );

    // Act
    renderWithProviders(<BudgetHistory />);

    // Assert
    const cards = await screen.findAllByTestId("budget-history-card");
    expect(cards[0].className).not.toContain("red");
    expect(cards[0]).toHaveTextContent("Remaining");
  });

  // TC-017-05
  // Given the Home page renders BudgetWidget and BudgetHistory together
  // When the page has loaded
  // Then exactly one "Edit budget" button is present on the page
  it("keeps exactly one editable budget box when combined with BudgetWidget", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockImplementation((_path, params) =>
      Promise.resolve(budgetFor(String(params?.month))),
    );

    // Act
    renderWithProviders(
      <>
        <BudgetWidget />
        <BudgetHistory />
      </>,
    );
    await screen.findByTestId("budget-widget");
    await screen.findAllByTestId("budget-history-card");

    // Assert
    expect(screen.getAllByRole("button", { name: /edit budget/i })).toHaveLength(1);
  });
});
