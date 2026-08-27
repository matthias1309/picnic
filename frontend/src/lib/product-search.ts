import type { ProductOut } from "../types";

/** Case- and diacritic-insensitive form for substring matching ("Äpfel" → "apfel"). */
function foldForSearch(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

/**
 * Products whose name contains `query`, most-bought first.
 *
 * Ranked by purchase_count rather than by match position: the article a user
 * searches for is overwhelmingly one they buy often, so "Bananen" must outrank
 * "Bio-Bananen" for the query "banan". Ties fall back to name order so the
 * list is stable across renders.
 *
 * An empty query yields no suggestions — dumping the full list is the problem
 * this search exists to solve.
 */
export function searchProducts(products: ProductOut[], query: string): ProductOut[] {
  const foldedQuery = foldForSearch(query.trim());
  if (foldedQuery === "") {
    return [];
  }

  return products
    .filter((product) => foldForSearch(product.name).includes(foldedQuery))
    .sort((a, b) => b.purchase_count - a.purchase_count || a.name.localeCompare(b.name, "de"));
}

/**
 * Products whose name contains `query`, ordered by name.
 *
 * Unlike `searchProducts`, an empty query lists *everything*: the article list
 * exists to work through the whole catalogue, above all the items the
 * categorisation backfill left unassigned, so hiding the list until something
 * is typed would defeat its purpose.
 */
export function filterProducts(products: ProductOut[], query: string): ProductOut[] {
  const foldedQuery = foldForSearch(query.trim());
  const matching =
    foldedQuery === ""
      ? products
      : products.filter((product) => foldForSearch(product.name).includes(foldedQuery));

  return [...matching].sort((a, b) => a.name.localeCompare(b.name, "de"));
}
