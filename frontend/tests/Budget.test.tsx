import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { BudgetWidget } from "../src/components/Budget/BudgetWidget";
import * as apiClient from "../src/api/client";
import { renderWithProviders } from "./test-utils";
import type { BudgetSettingOut, BudgetStatus } from "../src/types";

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

  // TC-022-04
  // Given spending within budget
  // When the widget renders
  // Then its state is exposed semantically as "within", not only by colour
  it("exposes the within-budget state semantically", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockResolvedValue(UNDER_BUDGET_FIXTURE);

    // Act
    renderWithProviders(<BudgetWidget />);

    // Assert
    const widget = await screen.findByTestId("budget-widget");
    expect(widget).toHaveAttribute("data-state", "within");
  });

  // TC-022-04
  // Given spending over budget
  // Then its state is exposed semantically as "over"
  it("exposes the over-budget state semantically", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockResolvedValue(OVER_BUDGET_FIXTURE);

    // Act
    renderWithProviders(<BudgetWidget />);

    // Assert
    const widget = await screen.findByTestId("budget-widget");
    expect(widget).toHaveAttribute("data-state", "over");
  });

  it("shows the over-budget state distinctly when spend exceeds the budget", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockResolvedValue(OVER_BUDGET_FIXTURE);

    // Act
    renderWithProviders(<BudgetWidget />);

    // Assert
    const widget = await screen.findByTestId("budget-widget");
    expect(widget).toHaveAttribute("data-state", "over");
    expect(widget).toHaveTextContent("350,00 €");
    expect(widget).toHaveTextContent("über Budget");
  });

  // TC-011-07
  // Given the budget widget shows a configured budget of 300.00 €
  // When the user clicks "Edit budget"
  // Then an input field is shown, pre-filled with "300"
  // And "Save" and "Cancel" controls are shown
  it("opens a pre-filled edit form when 'Edit budget' is clicked", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockResolvedValue(UNDER_BUDGET_FIXTURE);
    const user = userEvent.setup();

    // Act
    renderWithProviders(<BudgetWidget />);
    await screen.findByTestId("budget-widget");
    await user.click(screen.getByRole("button", { name: "Budget bearbeiten" }));

    // Assert
    expect(screen.getByRole("spinbutton")).toHaveValue(300);
    expect(screen.getByRole("button", { name: "Speichern" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Abbrechen" })).toBeInTheDocument();
  });

  // TC-011-08
  // Given the budget widget is in edit mode showing "300"
  // When the user changes the input to "350" and clicks "Save"
  // Then apiClient.putJson is called with ("/settings/budget", { monthly_budget_cents: 35000 })
  // And the edit form is closed
  // And the widget displays the updated budget (350,00 €)
  it("saves the new budget and updates the display", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson")
      .mockResolvedValueOnce(UNDER_BUDGET_FIXTURE)
      .mockResolvedValueOnce({ ...UNDER_BUDGET_FIXTURE, budget_cents: 35000 });
    const putJson = vi
      .spyOn(apiClient, "putJson")
      .mockResolvedValue({ monthly_budget_cents: 35000 } as BudgetSettingOut);
    const user = userEvent.setup();

    // Act
    renderWithProviders(<BudgetWidget />);
    await screen.findByTestId("budget-widget");
    await user.click(screen.getByRole("button", { name: "Budget bearbeiten" }));
    const input = screen.getByRole("spinbutton");
    await user.clear(input);
    await user.type(input, "350");
    await user.click(screen.getByRole("button", { name: "Speichern" }));

    // Assert
    expect(putJson).toHaveBeenCalledWith("/settings/budget", { monthly_budget_cents: 35000 });
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Speichern" })).not.toBeInTheDocument(),
    );
    const widget = await screen.findByTestId("budget-widget");
    expect(widget).toHaveTextContent("350,00 €");
  });

  // TC-011-09
  // Given the budget widget is in edit mode showing "300"
  // When the user changes the input to "350" and clicks "Cancel"
  // Then apiClient.putJson is not called
  // And the edit form is closed
  // And the widget still displays the original budget (300,00 €)
  it("discards changes when 'Cancel' is clicked", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockResolvedValue(UNDER_BUDGET_FIXTURE);
    const putJson = vi.spyOn(apiClient, "putJson");
    const user = userEvent.setup();

    // Act
    renderWithProviders(<BudgetWidget />);
    await screen.findByTestId("budget-widget");
    await user.click(screen.getByRole("button", { name: "Budget bearbeiten" }));
    const input = screen.getByRole("spinbutton");
    await user.clear(input);
    await user.type(input, "350");
    await user.click(screen.getByRole("button", { name: "Abbrechen" }));

    // Assert
    expect(putJson).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Speichern" })).not.toBeInTheDocument();
    const widget = screen.getByTestId("budget-widget");
    expect(widget).toHaveTextContent("300,00 €");
  });

  // TC-011-10
  // Given the budget widget is in edit mode
  // When the user changes the input to "-10" and clicks "Speichern"
  // Then apiClient.putJson is not called
  // And a validation message is shown
  // And the edit form remains open
  it("rejects a negative budget without sending a request", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockResolvedValue(UNDER_BUDGET_FIXTURE);
    const putJson = vi.spyOn(apiClient, "putJson");
    const user = userEvent.setup();

    // Act
    renderWithProviders(<BudgetWidget />);
    await screen.findByTestId("budget-widget");
    await user.click(screen.getByRole("button", { name: "Budget bearbeiten" }));
    const input = screen.getByRole("spinbutton");
    await user.clear(input);
    await user.type(input, "-10");
    await user.click(screen.getByRole("button", { name: "Speichern" }));

    // Assert
    expect(putJson).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Speichern" })).toBeInTheDocument();
    expect(screen.getByText("Bitte gib ein Budget von 0 oder mehr ein.")).toBeInTheDocument();
  });
});

describe("BudgetWidget German labels", () => {
  // TC-020-10
  // Given a budget response for month "2026-06"
  // When the budget widget renders
  // Then the card reads "Budget für Juni 2026" and never the raw API key
  it("renders the month as a German month name, not the raw API key", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockResolvedValue(UNDER_BUDGET_FIXTURE);

    // Act
    renderWithProviders(<BudgetWidget />);

    // Assert
    const widget = await screen.findByTestId("budget-widget");
    expect(widget).toHaveTextContent("Budget für Juni 2026");
    expect(widget).not.toHaveTextContent("2026-06");
  });

  // TC-020-11
  // Given spending under budget
  // Then the card reads "Verbleibend: 180,00 €"
  it("labels the remaining amount in German", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockResolvedValue(UNDER_BUDGET_FIXTURE);

    // Act
    renderWithProviders(<BudgetWidget />);

    // Assert
    const widget = await screen.findByTestId("budget-widget");
    expect(widget).toHaveTextContent("Verbleibend: 180,00 €");
  });

  it("labels the over-budget amount in German", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockResolvedValue(OVER_BUDGET_FIXTURE);

    // Act
    renderWithProviders(<BudgetWidget />);

    // Assert
    const widget = await screen.findByTestId("budget-widget");
    expect(widget).toHaveTextContent("50,00 € über Budget");
  });

  it("labels the edit form in German", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockResolvedValue(UNDER_BUDGET_FIXTURE);
    const user = userEvent.setup();

    // Act
    renderWithProviders(<BudgetWidget />);
    await screen.findByTestId("budget-widget");
    await user.click(screen.getByRole("button", { name: "Budget bearbeiten" }));

    // Assert
    expect(screen.getByLabelText("Monatsbudget (€)")).toBeInTheDocument();
    expect(screen.getByTestId("budget-widget")).toHaveTextContent("Budget für Juni 2026");
  });
});
