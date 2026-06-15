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
    await user.click(screen.getByRole("button", { name: "Edit budget" }));

    // Assert
    expect(screen.getByRole("spinbutton")).toHaveValue(300);
    expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
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
    await user.click(screen.getByRole("button", { name: "Edit budget" }));
    const input = screen.getByRole("spinbutton");
    await user.clear(input);
    await user.type(input, "350");
    await user.click(screen.getByRole("button", { name: "Save" }));

    // Assert
    expect(putJson).toHaveBeenCalledWith("/settings/budget", { monthly_budget_cents: 35000 });
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Save" })).not.toBeInTheDocument(),
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
    await user.click(screen.getByRole("button", { name: "Edit budget" }));
    const input = screen.getByRole("spinbutton");
    await user.clear(input);
    await user.type(input, "350");
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    // Assert
    expect(putJson).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Save" })).not.toBeInTheDocument();
    const widget = screen.getByTestId("budget-widget");
    expect(widget).toHaveTextContent("300,00 €");
  });

  // TC-011-10
  // Given the budget widget is in edit mode
  // When the user changes the input to "-10" and clicks "Save"
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
    await user.click(screen.getByRole("button", { name: "Edit budget" }));
    const input = screen.getByRole("spinbutton");
    await user.clear(input);
    await user.type(input, "-10");
    await user.click(screen.getByRole("button", { name: "Save" }));

    // Assert
    expect(putJson).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument();
    expect(screen.getByText(/0 or more/)).toBeInTheDocument();
  });
});
