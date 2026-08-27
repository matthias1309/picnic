import type { CategoryKey } from "../types";

/**
 * Chart colors, mirroring the Tailwind theme tokens.
 *
 * Recharts takes colors as props rather than class names, so the values are
 * repeated here instead of being read from the theme. Keep in sync with
 * `tailwind.config.js`: series = brand.500, grid = surface.border.
 */
export const CHART_COLORS = {
  series: "#2f6fdb",
  grid: "#e5e7eb",
  axis: "#6b7280",
} as const;

/**
 * One fixed colour per category, plus the "not assigned" bucket.
 *
 * Deliberately a map, not an array indexed by position: the category chart is
 * sorted by spend, so a positional palette would recolour every category
 * whenever the ranking changes between periods (ARCH-024 Key Decision 6).
 */
export const CATEGORY_COLORS: Record<CategoryKey | "uncategorized", string> = {
  fruit: "#e8743b",
  vegetables: "#4aa564",
  dairy: "#2f6fdb",
  bakery: "#b98a3c",
  meat: "#c0504d",
  fish: "#4bacc6",
  frozen: "#7ba7d7",
  ready_meals: "#8064a2",
  beverages: "#3aa6a0",
  pantry: "#9c8061",
  sweets: "#d96ba0",
  personal_care: "#6f9bd1",
  household: "#77797c",
  other: "#a0a4a8",
  uncategorized: "#c7cacd",
} as const;

/** Label for products that have not been assigned a category yet. */
export const UNCATEGORIZED_LABEL = "Nicht zugeordnet";
