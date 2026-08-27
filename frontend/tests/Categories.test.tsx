import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { CategorySpending } from "../src/components/Charts/CategorySpending";
import { ProductList } from "../src/components/Products/ProductList";
import * as apiClient from "../src/api/client";
import { renderWithProviders } from "./test-utils";
import type {
  Category,
  CategorySpending as CategorySpendingBucket,
  ProductOut,
} from "../src/types";

/**
 * Category tests (TEST-024).
 *
 * Traces: ARCH-024
 * Verifies: REQ-024 (AC-024-11, AC-024-12)
 */

const CATEGORIES_FIXTURE: Category[] = [
  { key: "dairy", label: "Milchprodukte" },
  { key: "beverages", label: "Getränke" },
  { key: "sweets", label: "Süßwaren" },
];

const BY_CATEGORY_FIXTURE: CategorySpendingBucket[] = [
  { category_key: "dairy", total_cents: 2500 },
  { category_key: "beverages", total_cents: 1000 },
  { category_key: null, total_cents: 150 },
];

const PRODUCTS_FIXTURE: ProductOut[] = [
  { id: 1, name: "Bio Vollmilch 1L", purchase_count: 8, category_key: "dairy" },
  { id: 2, name: "Apfelsaft 1L", purchase_count: 4, category_key: "beverages" },
  { id: 3, name: "Ahoi-Brause Sortiment", purchase_count: 1, category_key: null },
];

function mockFetch(buckets: CategorySpendingBucket[]) {
  return vi.spyOn(apiClient, "fetchJson").mockImplementation((path) => {
    if (path === "/categories") return Promise.resolve(CATEGORIES_FIXTURE);
    if (path === "/stats/by-category") return Promise.resolve(buckets);
    if (path === "/products") return Promise.resolve(PRODUCTS_FIXTURE);
    throw new Error(`unexpected path: ${path}`);
  });
}

describe("CategorySpending", () => {
  // TC-024-19
  // Given the API returns category spending buckets
  // When the "Statistiken" page is rendered
  // Then a "Ausgaben nach Kategorie" heading is shown
  // And each returned category's German label is shown
  it("should show the category breakdown when spending exists", async () => {
    // Arrange
    mockFetch(BY_CATEGORY_FIXTURE);

    // Act
    renderWithProviders(<CategorySpending />);

    // Assert
    expect(await screen.findByText("Ausgaben nach Kategorie")).toBeInTheDocument();
    expect(await screen.findByText("Milchprodukte")).toBeInTheDocument();
    expect(await screen.findByText("Getränke")).toBeInTheDocument();
    expect(await screen.findByText("Nicht zugeordnet")).toBeInTheDocument();
    expect(await screen.findByText("25,00 €")).toBeInTheDocument();
  });

  // TC-024-19
  // Given the API returns no buckets
  // When the page is rendered
  // Then the empty state is shown
  it("should show the empty state when no spending exists in the period", async () => {
    // Arrange
    mockFetch([]);

    // Act
    renderWithProviders(<CategorySpending />);

    // Assert
    expect(await screen.findByText("Noch keine Ausgabendaten vorhanden.")).toBeInTheDocument();
  });
});

describe("Articles page", () => {
  // TC-024-20
  // Given the API returns three products with different categories
  // When the "Artikel" page is rendered
  // Then all three products are listed with their category
  it("should list every product with its current category", async () => {
    // Arrange
    mockFetch(BY_CATEGORY_FIXTURE);

    // Act
    renderWithProviders(<ProductList />);

    // Assert
    const list = await screen.findByTestId("product-list");
    expect(within(list).getAllByRole("listitem")).toHaveLength(3);
    expect(
      await screen.findByRole("combobox", { name: "Kategorie für Bio Vollmilch 1L" }),
    ).toHaveValue("dairy");
    expect(
      screen.getByRole("combobox", { name: "Kategorie für Ahoi-Brause Sortiment" }),
    ).toHaveValue("");
  });

  // TC-024-20
  // When the user types a product name fragment into the search field
  // Then only matching products remain listed
  it("should filter the list by the search term", async () => {
    // Arrange
    mockFetch(BY_CATEGORY_FIXTURE);
    renderWithProviders(<ProductList />);
    await screen.findByTestId("product-list");

    // Act
    await userEvent.type(screen.getByRole("searchbox", { name: "Artikel suchen" }), "milch");

    // Assert
    const list = screen.getByTestId("product-list");
    expect(within(list).getAllByRole("listitem")).toHaveLength(1);
    expect(within(list).getByText("Bio Vollmilch 1L")).toBeInTheDocument();
  });

  // TC-024-20
  // When the user selects a different category for a product
  // Then PUT /api/products/{id}/category is sent with the chosen key
  // And the row shows the new category without a page reload
  it("should send the new category when the dropdown changes", async () => {
    // Arrange
    mockFetch(BY_CATEGORY_FIXTURE);
    const putJson = vi.spyOn(apiClient, "putJson").mockResolvedValue({
      ...PRODUCTS_FIXTURE[2],
      category_key: "sweets",
    });
    renderWithProviders(<ProductList />);

    // Act
    const select = await screen.findByRole("combobox", {
      name: "Kategorie für Ahoi-Brause Sortiment",
    });
    await userEvent.selectOptions(select, "sweets");

    // Assert
    expect(putJson).toHaveBeenCalledWith("/products/3/category", { category_key: "sweets" });
  });
});
