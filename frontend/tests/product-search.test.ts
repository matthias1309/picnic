import { describe, expect, it } from "vitest";
import { searchProducts } from "../src/lib/product-search";
import type { ProductOut } from "../src/types";

function product(name: string, purchaseCount: number, id = name.length): ProductOut {
  return { id, name, purchase_count: purchaseCount, category_key: null };
}

describe("searchProducts", () => {
  // TC-021-01
  // Given products "Bananen", "Bio-Bananen" and "Milch"
  // When searchProducts is called with "banan"
  // Then only the two banana products are returned
  it("returns only products whose name contains the query", () => {
    // Arrange
    const products = [
      product("Bananen", 10, 1),
      product("Bio-Bananen", 3, 2),
      product("Milch", 8, 3),
    ];

    // Act
    const matches = searchProducts(products, "banan");

    // Assert
    expect(matches.map((match) => match.name)).toEqual(["Bananen", "Bio-Bananen"]);
  });

  // TC-021-02
  // Given products with umlauts and mixed case
  // When searchProducts is called with an unaccented lowercase query
  // Then they are still matched
  it("matches regardless of case", () => {
    const products = [product("Bananen", 1)];

    expect(searchProducts(products, "BANANEN")).toHaveLength(1);
  });

  it("matches regardless of diacritics", () => {
    const products = [product("Äpfel", 1, 1), product("Müsli", 1, 2)];

    expect(searchProducts(products, "apfel").map((m) => m.name)).toEqual(["Äpfel"]);
    expect(searchProducts(products, "musli").map((m) => m.name)).toEqual(["Müsli"]);
  });

  // TC-021-03
  // Given "Bio-Bananen" (2) supplied before "Bananen" (30)
  // When searchProducts is called with "banan"
  // Then the most-bought product is ranked first
  it("ranks matches by purchase count, most bought first", () => {
    // Arrange — deliberately supplied in the reverse of the expected order
    const products = [product("Bio-Bananen", 2, 1), product("Bananen", 30, 2)];

    // Act
    const matches = searchProducts(products, "banan");

    // Assert
    expect(matches.map((match) => match.name)).toEqual(["Bananen", "Bio-Bananen"]);
  });

  it("falls back to name order when purchase counts are equal", () => {
    // Arrange
    const products = [product("Zucker", 5, 1), product("Apfel", 5, 2)];

    // Act
    const matches = searchProducts(products, "e");

    // Assert
    expect(matches.map((match) => match.name)).toEqual(["Apfel", "Zucker"]);
  });

  // TC-021-04
  // Given a non-empty product list
  // When the query is empty or whitespace only
  // Then nothing is suggested — the picker must not dump the full list
  it("returns nothing for an empty or whitespace-only query", () => {
    const products = [product("Bananen", 10)];

    expect(searchProducts(products, "")).toEqual([]);
    expect(searchProducts(products, "   ")).toEqual([]);
  });
});
