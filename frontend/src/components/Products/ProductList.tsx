import { useState } from "react";
import { useCategories } from "../../hooks/useCategories";
import { useProducts, useUpdateProductCategory } from "../../hooks/useProducts";
import { UNCATEGORIZED_LABEL } from "../../lib/chart-theme";
import { filterProducts } from "../../lib/product-search";
import type { CategoryKey } from "../../types";
import { EmptyState } from "../common/EmptyState";
import { ErrorMessage } from "../common/ErrorMessage";
import { LoadingSpinner } from "../common/LoadingSpinner";
import { Card } from "../ui/Card";
import { SectionHeader } from "../ui/SectionHeader";

export function ProductList() {
  const [query, setQuery] = useState("");
  const products = useProducts();
  const categories = useCategories();
  const updateCategory = useUpdateProductCategory();

  const visibleProducts = products.data ? filterProducts(products.data, query) : undefined;

  return (
    <Card>
      <SectionHeader title="Artikel" />

      <label className="block">
        <span className="sr-only">Artikel suchen</span>
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Artikel suchen…"
          className="w-full rounded-lg border border-surface-border px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
        />
      </label>

      {(products.isLoading || categories.isLoading) && <LoadingSpinner />}
      {products.isError && (
        <ErrorMessage message="Artikel konnten nicht geladen werden." onRetry={products.refetch} />
      )}
      {visibleProducts && visibleProducts.length === 0 && (
        <EmptyState message="Keine Artikel gefunden." />
      )}
      {visibleProducts && visibleProducts.length > 0 && (
        <ul data-testid="product-list" className="mt-4 divide-y divide-surface-border">
          {visibleProducts.map((product) => (
            <li
              key={product.id}
              className="flex flex-wrap items-center gap-3 py-2.5 text-sm sm:flex-nowrap"
            >
              <span className="min-w-0 flex-1 truncate text-gray-900">{product.name}</span>
              <span className="tabular-nums text-gray-500">{product.purchase_count}×</span>
              <label className="shrink-0">
                <span className="sr-only">Kategorie für {product.name}</span>
                <select
                  value={product.category_key ?? ""}
                  disabled={!categories.data}
                  onChange={(event) =>
                    updateCategory.mutate({
                      productId: product.id,
                      categoryKey: event.target.value as CategoryKey,
                    })
                  }
                  className="rounded-lg border border-surface-border bg-surface px-2 py-1.5 text-sm text-gray-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                >
                  <option value="" disabled>
                    {UNCATEGORIZED_LABEL}
                  </option>
                  {categories.data?.map((category) => (
                    <option key={category.key} value={category.key}>
                      {category.label}
                    </option>
                  ))}
                </select>
              </label>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
