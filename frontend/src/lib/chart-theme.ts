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
