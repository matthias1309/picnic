import { useId, useMemo, useState } from "react";
import type { KeyboardEvent } from "react";
import { searchProducts } from "../../lib/product-search";
import type { ProductOut } from "../../types";

/** Keeps the suggestion panel short — the long scrolling list is what this replaces. */
const MAX_SUGGESTIONS = 8;

const NO_HIGHLIGHT = -1;

interface ProductComboboxProps {
  products: ProductOut[];
  selectedProductId: number | null;
  onSelect: (productId: number | null) => void;
}

/**
 * Type-to-search picker for a single article, following the WAI-ARIA combobox
 * pattern.
 *
 * Owns only the transient query and highlight; the selection itself stays with
 * the caller, so the price-history data flow is unaffected by how an article
 * gets picked.
 */
export function ProductCombobox({ products, selectedProductId, onSelect }: ProductComboboxProps) {
  const selectedProduct = products.find((product) => product.id === selectedProductId);
  // null means "not edited yet" — the input then shows whatever is selected, so a
  // remount before /products has resolved still labels itself once the list arrives.
  const [draftQuery, setDraftQuery] = useState<string | null>(null);
  const query = draftQuery ?? selectedProduct?.name ?? "";
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(NO_HIGHLIGHT);
  const listboxId = useId();

  const suggestions = useMemo(
    () => searchProducts(products, query).slice(0, MAX_SUGGESTIONS),
    [products, query],
  );

  const optionId = (index: number) => `${listboxId}-option-${index}`;

  const selectProduct = (product: ProductOut) => {
    setDraftQuery(product.name);
    setIsOpen(false);
    setHighlightedIndex(NO_HIGHLIGHT);
    onSelect(product.id);
  };

  const handleQueryChange = (value: string) => {
    setDraftQuery(value);
    setIsOpen(true);
    setHighlightedIndex(NO_HIGHLIGHT);
    if (value.trim() === "") {
      onSelect(null);
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") {
      setIsOpen(false);
      setHighlightedIndex(NO_HIGHLIGHT);
      return;
    }

    if (event.key === "Enter") {
      const highlighted = suggestions[highlightedIndex];
      if (highlighted) {
        event.preventDefault();
        selectProduct(highlighted);
      }
      return;
    }

    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setIsOpen(true);
      const step = event.key === "ArrowDown" ? 1 : -1;
      const lastIndex = suggestions.length - 1;
      setHighlightedIndex((current) => Math.min(Math.max(current + step, 0), lastIndex));
    }
  };

  const isListVisible = isOpen && query.trim() !== "";

  return (
    <div className="relative">
      <input
        type="text"
        role="combobox"
        aria-label="Artikel"
        aria-expanded={isListVisible}
        aria-controls={listboxId}
        aria-autocomplete="list"
        aria-activedescendant={
          highlightedIndex === NO_HIGHLIGHT ? undefined : optionId(highlightedIndex)
        }
        value={query}
        placeholder="Artikel suchen…"
        onChange={(event) => handleQueryChange(event.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={() => setIsOpen(true)}
        onBlur={(event) => {
          // Keep the list open when focus moves into it, or clicking an option
          // would be swallowed by the input blurring first.
          if (!event.currentTarget.parentElement?.contains(event.relatedTarget)) {
            setIsOpen(false);
          }
        }}
        className="w-56 rounded border border-gray-300 px-2 py-1 text-sm"
      />

      {isListVisible && (
        <div className="absolute z-10 mt-1 w-72 rounded border border-gray-200 bg-white shadow-lg">
          {suggestions.length === 0 ? (
            <p className="px-3 py-2 text-sm text-gray-500">Kein Artikel gefunden.</p>
          ) : (
            <ul id={listboxId} role="listbox" aria-label="Artikelvorschläge">
              {suggestions.map((product, index) => (
                <li
                  key={product.id}
                  id={optionId(index)}
                  role="option"
                  aria-selected={product.id === selectedProductId}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => selectProduct(product)}
                  onMouseEnter={() => setHighlightedIndex(index)}
                  className={`flex cursor-pointer items-center justify-between px-3 py-2 text-sm ${
                    index === highlightedIndex ? "bg-gray-100" : ""
                  }`}
                >
                  <span>{product.name}</span>
                  <span className="text-xs text-gray-500">{product.purchase_count}× gekauft</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
