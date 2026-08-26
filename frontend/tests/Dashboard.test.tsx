import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Dashboard } from "../src/components/Dashboard";
import * as apiClient from "../src/api/client";
import { renderWithProviders } from "./test-utils";
import type { SummaryStats } from "../src/types";

const SUMMARY_FIXTURE: SummaryStats = {
  total_spend_cents: 123456,
  receipt_count: 42,
  distinct_product_count: 17,
  average_basket_cents: 2940,
  current_month_spend_cents: 5500,
};

describe("Dashboard", () => {
  // TC-005-01
  // Given the API is reachable
  // When the user opens the dashboard home page
  // Then headline statistics from /api/stats/summary are displayed
  // And loading and error states are shown while data is fetched
  it("shows a loading state while fetching summary statistics", () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockReturnValue(new Promise(() => {}));

    // Act
    renderWithProviders(<Dashboard />);

    // Assert
    expect(screen.getByRole("status", { name: /lädt/i })).toBeInTheDocument();
  });

  it("displays headline statistics from /api/stats/summary when loaded", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockResolvedValue(SUMMARY_FIXTURE);

    // Act
    renderWithProviders(<Dashboard />);

    // Assert
    expect(await screen.findByText("1.234,56 €")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("Gesamtausgaben")).toBeInTheDocument();
    expect(screen.getByText("Kassenbons")).toBeInTheDocument();
    expect(screen.getByText("Verschiedene Artikel")).toBeInTheDocument();
    expect(screen.getByText("Durchschnittlicher Einkauf")).toBeInTheDocument();
    expect(screen.getByText("Ausgaben diesen Monat")).toBeInTheDocument();
    expect(screen.getByText("17")).toBeInTheDocument();
    expect(screen.getByText("29,40 €")).toBeInTheDocument();
    expect(screen.getByText("55,00 €")).toBeInTheDocument();
  });

  it("shows an error state when the summary request fails", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockRejectedValue(new Error("network error"));

    // Act
    renderWithProviders(<Dashboard />);

    // Assert
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Zusammenfassung konnte nicht geladen werden.");
  });

  // TC-005-06
  // Given the dashboard fetches data from the API
  // When requests are in flight, succeed, or fail
  // Then TanStack Query handles caching, loading, and error states
  // And the UI degrades gracefully (empty states, retry) without crashing
  it("retries the request when the retry button is clicked after an error", async () => {
    // Arrange
    const fetchJsonMock = vi
      .spyOn(apiClient, "fetchJson")
      .mockRejectedValueOnce(new Error("network error"))
      .mockResolvedValueOnce(SUMMARY_FIXTURE);

    renderWithProviders(<Dashboard />);
    const retryButton = await screen.findByRole("button", { name: /erneut versuchen/i });

    // Act
    retryButton.click();

    // Assert
    await waitFor(() => expect(fetchJsonMock).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("1.234,56 €")).toBeInTheDocument();
  });

  it("renders zero values without crashing when the summary is empty", async () => {
    // Arrange
    const emptySummary: SummaryStats = {
      total_spend_cents: 0,
      receipt_count: 0,
      distinct_product_count: 0,
      average_basket_cents: 0,
      current_month_spend_cents: 0,
    };
    vi.spyOn(apiClient, "fetchJson").mockResolvedValue(emptySummary);

    // Act
    renderWithProviders(<Dashboard />);

    // Assert
    expect(await screen.findAllByText("0,00 €")).toHaveLength(3);
    expect(screen.getAllByText("0")).toHaveLength(2);
  });
});
