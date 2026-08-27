import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ProductCombobox } from "../src/components/Charts/ProductCombobox";
import type { ProductOut } from "../src/types";

const PRODUCTS: ProductOut[] = [
  { id: 1, name: "Bananen", purchase_count: 30, category_key: null },
  { id: 2, name: "Bio-Bananen", purchase_count: 2, category_key: null },
  { id: 3, name: "Milch", purchase_count: 12, category_key: null },
];

function renderCombobox(selectedProductId: number | null = null) {
  const onSelect = vi.fn();
  render(
    <ProductCombobox
      products={PRODUCTS}
      selectedProductId={selectedProductId}
      onSelect={onSelect}
    />,
  );
  return { onSelect, input: screen.getByRole("combobox", { name: "Artikel" }) };
}

describe("ProductCombobox", () => {
  // TC-021-05
  // Given the picker with three products
  // When the user types "banan"
  // Then only the matching products are offered, most bought first, with counts
  it("filters and ranks the suggestions as the user types", async () => {
    // Arrange
    const { input } = renderCombobox();

    // Act
    await userEvent.type(input, "banan");

    // Assert
    const options = screen.getAllByRole("option");
    expect(options.map((option) => option.textContent)).toEqual([
      expect.stringContaining("Bananen"),
      expect.stringContaining("Bio-Bananen"),
    ]);
    expect(screen.queryByText("Milch")).not.toBeInTheDocument();
    expect(options[0]).toHaveTextContent("30");
  });

  // TC-021-06
  // Given suggestions are shown
  // When the user clicks one
  // Then it is reported, shown in the input, and the list closes
  it("reports the clicked product and closes the list", async () => {
    // Arrange
    const { onSelect, input } = renderCombobox();
    await userEvent.type(input, "banan");

    // Act
    await userEvent.click(screen.getByRole("option", { name: /^Bananen/ }));

    // Assert
    expect(onSelect).toHaveBeenCalledWith(1);
    expect(input).toHaveValue("Bananen");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  // TC-021-07
  // Given two suggestions are shown
  // When the user arrows down twice and presses Enter
  // Then the second suggestion is selected
  it("selects a suggestion with the arrow keys and Enter", async () => {
    // Arrange
    const { onSelect, input } = renderCombobox();
    await userEvent.type(input, "banan");
    const options = screen.getAllByRole("option");

    // Act
    await userEvent.keyboard("{ArrowDown}");
    expect(input).toHaveAttribute("aria-activedescendant", options[0].id);
    await userEvent.keyboard("{ArrowDown}");
    expect(input).toHaveAttribute("aria-activedescendant", options[1].id);
    await userEvent.keyboard("{Enter}");

    // Assert
    expect(onSelect).toHaveBeenCalledWith(2);
  });

  // TC-021-08
  // When the user presses Escape
  // Then the list closes and nothing is selected
  it("closes the list on Escape without changing the selection", async () => {
    // Arrange
    const { onSelect, input } = renderCombobox();
    await userEvent.type(input, "banan");
    expect(screen.getByRole("listbox")).toBeInTheDocument();

    // Act
    await userEvent.keyboard("{Escape}");

    // Assert
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(onSelect).not.toHaveBeenCalled();
  });

  // TC-021-09
  // Given the picker is rendered
  // Then it exposes the combobox role and reports its expanded state
  it("exposes the ARIA combobox contract", async () => {
    // Arrange
    const { input } = renderCombobox();

    // Assert — collapsed
    expect(input).toHaveAttribute("aria-expanded", "false");

    // Act
    await userEvent.type(input, "banan");

    // Assert — expanded
    expect(input).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("listbox")).toBeInTheDocument();
  });

  // TC-021-10
  // When no product matches the query
  // Then the picker says so rather than showing an empty list
  it("reports when no product matches", async () => {
    // Arrange
    const { onSelect, input } = renderCombobox();

    // Act
    await userEvent.type(input, "xyzzy");

    // Assert
    expect(screen.getByText("Kein Artikel gefunden.")).toBeInTheDocument();
    expect(screen.queryAllByRole("option")).toHaveLength(0);
    expect(onSelect).not.toHaveBeenCalled();
  });

  // TC-021-11
  // Given a product is selected
  // When the user clears the input
  // Then the selection is cleared
  it("clears the selection when the input is emptied", async () => {
    // Arrange
    const { onSelect, input } = renderCombobox(1);

    // Act
    await userEvent.clear(input);

    // Assert
    expect(onSelect).toHaveBeenCalledWith(null);
  });
});
