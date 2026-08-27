import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PriceHistory } from "../src/components/Charts/PriceHistory";
import { PurchaseStats } from "../src/components/Charts/PurchaseStats";
import * as apiClient from "../src/api/client";
import { useUiStore } from "../src/store/useUiStore";
import { renderWithProviders } from "./test-utils";
import type { PriceTrend, ProductOut, SpendingOverTime, TopItem } from "../src/types";

const PRODUCTS_FIXTURE: ProductOut[] = [
  { id: 1, name: "Bananas", purchase_count: 5, category_key: null },
];

const PRICE_TREND_FIXTURE: PriceTrend = {
  product_id: 1,
  product_name: "Bananas",
  points: [
    { date: "2026-01-01", unit_price_cents: 99, quantity: 1 },
    { date: "2026-02-01", unit_price_cents: 109, quantity: 1 },
  ],
  min_price_cents: 99,
  max_price_cents: 109,
  avg_price_cents: 104,
};

const SPENDING_FIXTURE: SpendingOverTime = {
  granularity: "month",
  buckets: [
    { period: "2026-01", total_cents: 10000 },
    { period: "2026-02", total_cents: 20000 },
  ],
};

const TOP_ITEMS_FIXTURE: TopItem[] = [
  { product_id: 1, product_name: "Bananas", total_quantity: 10, total_spend_cents: 990 },
  { product_id: 2, product_name: "Milk", total_quantity: 5, total_spend_cents: 750 },
];

beforeEach(() => {
  useUiStore.setState({
    statsPeriod: "month",
    priceHistoryRange: "6m",
    selectedProductId: null,
    receiptsOffset: 0,
  });
});

describe("PriceHistory", () => {
  // TC-005-02, TC-021-12
  // Given a product with price history is selected
  // When the user views the price history chart
  // Then a Recharts line chart renders price over time
  // And the time range is configurable (e.g. 3m / 6m / 12m / all)
  it("renders a line chart with min/max/avg once a product is selected", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockImplementation((path) => {
      if (path === "/products") return Promise.resolve(PRODUCTS_FIXTURE);
      if (path.startsWith("/stats/price-trend")) return Promise.resolve(PRICE_TREND_FIXTURE);
      throw new Error(`unexpected path: ${path}`);
    });

    renderWithProviders(<PriceHistory />);
    expect(
      screen.getByText("Wähle einen Artikel, um seinen Preisverlauf zu sehen."),
    ).toBeInTheDocument();

    // Act
    const picker = await screen.findByRole("combobox", { name: "Artikel" });
    await userEvent.type(picker, "banan");
    await userEvent.click(await screen.findByRole("option", { name: /^Bananas/ }));

    // Assert
    expect(await screen.findByTestId("price-history-chart")).toBeInTheDocument();
    expect(screen.getByText(/min\. 0,99/i)).toBeInTheDocument();
    expect(screen.getByText(/max\. 1,09/i)).toBeInTheDocument();
    expect(screen.getByText(/Ø 1,04/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Preisverlauf" })).toBeInTheDocument();
  });

  // TC-021-13
  it("offers configurable time ranges (3 Mon. / 6 Mon. / 12 Mon. / Gesamt)", async () => {
    // Arrange
    const fetchJsonMock = vi.spyOn(apiClient, "fetchJson").mockImplementation((path) => {
      if (path === "/products") return Promise.resolve(PRODUCTS_FIXTURE);
      if (path.startsWith("/stats/price-trend")) return Promise.resolve(PRICE_TREND_FIXTURE);
      throw new Error(`unexpected path: ${path}`);
    });

    renderWithProviders(<PriceHistory />);
    const picker = await screen.findByRole("combobox", { name: "Artikel" });
    await userEvent.type(picker, "banan");
    await userEvent.click(await screen.findByRole("option", { name: /^Bananas/ }));
    await screen.findByTestId("price-history-chart");

    // Act
    const rangeGroup = screen.getByRole("group", { name: /zeitraum/i });
    const threeMonthButton = findButtonByText(rangeGroup, "3 Mon.");
    expect(findButtonByText(rangeGroup, "6 Mon.")).toBeInTheDocument();
    expect(findButtonByText(rangeGroup, "12 Mon.")).toBeInTheDocument();
    expect(findButtonByText(rangeGroup, "Gesamt")).toBeInTheDocument();
    await userEvent.click(threeMonthButton);

    // Assert
    expect(threeMonthButton).toHaveAttribute("aria-pressed", "true");
    expect(fetchJsonMock).toHaveBeenCalledWith(
      "/stats/price-trend/1",
      expect.objectContaining({ from_date: expect.any(String) }),
    );
  });
});

describe("PurchaseStats", () => {
  // TC-005-03
  // Given parsed data exists
  // When the user opens the statistics view
  // Then top purchased items and spending-over-time are visualized
  // And the user can switch the aggregation period (week/month)
  it("renders top purchased items and spending-over-time", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockImplementation((path) => {
      if (path === "/stats/top-items") return Promise.resolve(TOP_ITEMS_FIXTURE);
      if (path === "/stats/spending") return Promise.resolve(SPENDING_FIXTURE);
      throw new Error(`unexpected path: ${path}`);
    });

    // Act
    renderWithProviders(<PurchaseStats />);

    // Assert
    expect(await screen.findByTestId("spending-chart")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ausgaben im Zeitverlauf" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Meistgekaufte Artikel" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Monat" })).toBeInTheDocument();
    const topItemsList = await screen.findByTestId("top-items-list");
    expect(topItemsList).toHaveTextContent("Bananas");
    expect(topItemsList).toHaveTextContent("Milk");
  });

  it("switches the aggregation period between week and month", async () => {
    // Arrange
    const fetchJsonMock = vi.spyOn(apiClient, "fetchJson").mockImplementation((path) => {
      if (path === "/stats/top-items") return Promise.resolve(TOP_ITEMS_FIXTURE);
      if (path === "/stats/spending") return Promise.resolve(SPENDING_FIXTURE);
      throw new Error(`unexpected path: ${path}`);
    });

    renderWithProviders(<PurchaseStats />);
    await screen.findByTestId("spending-chart");

    // Act
    const weekButton = screen.getByRole("button", { name: "Woche" });
    await userEvent.click(weekButton);

    // Assert
    expect(weekButton).toHaveAttribute("aria-pressed", "true");
    expect(fetchJsonMock).toHaveBeenCalledWith("/stats/spending", { granularity: "week" });
  });
});

function findButtonByText(container: HTMLElement, name: string): HTMLElement {
  const button = Array.from(container.querySelectorAll("button")).find(
    (el) => el.textContent?.trim() === name,
  );
  if (!button) {
    throw new Error(`Button "${name}" not found`);
  }
  return button;
}

describe("PriceHistory German empty states", () => {
  // TC-020-07
  // Given a product is selected whose trend has no points
  // Then "Für diesen Artikel liegt kein Preisverlauf vor." is displayed
  it("reports an empty price trend in German", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockImplementation((path) => {
      if (path === "/products") return Promise.resolve(PRODUCTS_FIXTURE);
      if (path.startsWith("/stats/price-trend")) {
        return Promise.resolve({ ...PRICE_TREND_FIXTURE, points: [] });
      }
      throw new Error(`unexpected path: ${path}`);
    });

    renderWithProviders(<PriceHistory />);
    const picker = await screen.findByRole("combobox", { name: "Artikel" });

    // Act
    await userEvent.type(picker, "banan");
    await userEvent.click(await screen.findByRole("option", { name: /^Bananas/ }));

    // Assert
    expect(
      await screen.findByText("Für diesen Artikel liegt kein Preisverlauf vor."),
    ).toBeInTheDocument();
  });
});
