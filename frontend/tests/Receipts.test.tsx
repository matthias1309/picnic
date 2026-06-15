import { Route, Routes } from "react-router-dom";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Receipts } from "../src/pages/Receipts";
import * as apiClient from "../src/api/client";
import { useUiStore } from "../src/store/useUiStore";
import { renderWithProviders } from "./test-utils";
import type { PaginatedReceipts, ReceiptDetail } from "../src/types";

const RECEIPTS_FIXTURE: PaginatedReceipts = {
  items: [
    {
      id: 3,
      received_date: "2026-06-10T12:00:00Z",
      from_address: "picnic@picnic.de",
      item_count: 5,
      total_cents: 4200,
    },
    {
      id: 2,
      received_date: "2026-06-03T12:00:00Z",
      from_address: "picnic@picnic.de",
      item_count: 3,
      total_cents: 1800,
    },
    {
      id: 1,
      received_date: "2026-05-27T12:00:00Z",
      from_address: "picnic@picnic.de",
      item_count: 8,
      total_cents: 6750,
    },
  ],
  total: 3,
  limit: 20,
  offset: 0,
};

const RECEIPT_DETAIL_FIXTURE: ReceiptDetail = {
  id: 3,
  received_date: "2026-06-10T12:00:00Z",
  from_address: "picnic@picnic.de",
  items: [
    { product_name: "Bananas", quantity: 2, unit_price_cents: 99, line_total_cents: 198 },
    { product_name: "Milk", quantity: 1, unit_price_cents: 109, line_total_cents: 109 },
  ],
  total_cents: 307,
};

beforeEach(() => {
  useUiStore.setState({
    statsPeriod: "month",
    priceHistoryRange: "6m",
    selectedProductId: null,
    receiptsOffset: 0,
  });
});

describe("Receipts", () => {
  // TC-005-04
  // Given receipts exist
  // When the user opens the receipts list
  // Then receipts are shown paginated, sorted by date descending
  // And selecting a receipt shows its line items with quantities and prices
  it("shows receipts paginated and sorted by date descending", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockImplementation((path) => {
      if (path === "/receipts") return Promise.resolve(RECEIPTS_FIXTURE);
      throw new Error(`unexpected path: ${path}`);
    });

    // Act
    renderWithProviders(
      <Routes>
        <Route path="/receipts" element={<Receipts />} />
      </Routes>,
      { route: "/receipts" },
    );

    // Assert
    const list = await screen.findByTestId("receipt-list");
    const rows = list.querySelectorAll("li");
    expect(rows).toHaveLength(3);
    expect(rows[0]).toHaveTextContent("10.6.2026");
    expect(rows[1]).toHaveTextContent("3.6.2026");
    expect(rows[2]).toHaveTextContent("27.5.2026");
    expect(screen.getByText("1-3 of 3")).toBeInTheDocument();
  });

  it("shows a receipt's line items with quantities and prices when selected", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockImplementation((path) => {
      if (path === "/receipts/3") return Promise.resolve(RECEIPT_DETAIL_FIXTURE);
      throw new Error(`unexpected path: ${path}`);
    });

    // Act
    renderWithProviders(
      <Routes>
        <Route path="/receipts/:id" element={<Receipts />} />
      </Routes>,
      { route: "/receipts/3" },
    );

    // Assert
    const detail = await screen.findByTestId("receipt-detail");
    expect(detail).toHaveTextContent("Bananas");
    expect(detail).toHaveTextContent("2x");
    expect(detail).toHaveTextContent("0,99 €");
    expect(detail).toHaveTextContent("1,98 €");
    expect(detail).toHaveTextContent("Milk");
    expect(detail).toHaveTextContent("3,07 €");
  });

  // TC-009-05
  // Given the user is viewing a receipt's detail page
  // When the page is rendered
  // Then a button labeled "Delete receipt" is visible
  it("shows a delete receipt button on the receipt detail page", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockImplementation((path) => {
      if (path === "/receipts/3") return Promise.resolve(RECEIPT_DETAIL_FIXTURE);
      throw new Error(`unexpected path: ${path}`);
    });

    // Act
    renderWithProviders(
      <Routes>
        <Route path="/receipts/:id" element={<Receipts />} />
      </Routes>,
      { route: "/receipts/3" },
    );

    // Assert
    await screen.findByTestId("receipt-detail");
    expect(screen.getByRole("button", { name: "Delete receipt" })).toBeInTheDocument();
  });

  // TC-009-06
  // Given the user is viewing a receipt's detail page
  // And window.confirm is mocked to return true
  // When they click "Delete receipt"
  // Then a DELETE request is sent to /receipts/{id}
  // And the user is navigated to /receipts
  it("deletes the receipt and navigates to the list when confirmed", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockImplementation((path) => {
      if (path === "/receipts/3") return Promise.resolve(RECEIPT_DETAIL_FIXTURE);
      if (path === "/receipts") return Promise.resolve(RECEIPTS_FIXTURE);
      throw new Error(`unexpected path: ${path}`);
    });
    const deleteJson = vi.spyOn(apiClient, "deleteJson").mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();

    // Act
    renderWithProviders(
      <Routes>
        <Route path="/receipts" element={<Receipts />} />
        <Route path="/receipts/:id" element={<Receipts />} />
      </Routes>,
      { route: "/receipts/3" },
    );
    await screen.findByTestId("receipt-detail");
    await user.click(screen.getByRole("button", { name: "Delete receipt" }));

    // Assert
    expect(deleteJson).toHaveBeenCalledWith("/receipts/3");
    await waitFor(() => expect(screen.getByTestId("receipt-list")).toBeInTheDocument());
  });

  // TC-009-07
  // Given the user is viewing a receipt's detail page
  // And window.confirm is mocked to return false
  // When they click "Delete receipt"
  // Then no DELETE request is sent
  // And the receipt detail remains visible
  it("does not delete the receipt when the confirmation is cancelled", async () => {
    // Arrange
    vi.spyOn(apiClient, "fetchJson").mockImplementation((path) => {
      if (path === "/receipts/3") return Promise.resolve(RECEIPT_DETAIL_FIXTURE);
      throw new Error(`unexpected path: ${path}`);
    });
    const deleteJson = vi.spyOn(apiClient, "deleteJson").mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const user = userEvent.setup();

    // Act
    renderWithProviders(
      <Routes>
        <Route path="/receipts/:id" element={<Receipts />} />
      </Routes>,
      { route: "/receipts/3" },
    );
    await screen.findByTestId("receipt-detail");
    await user.click(screen.getByRole("button", { name: "Delete receipt" }));

    // Assert
    expect(deleteJson).not.toHaveBeenCalled();
    expect(screen.getByTestId("receipt-detail")).toBeInTheDocument();
  });
});
