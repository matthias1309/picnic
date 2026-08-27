import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useCategories } from "../../hooks/useCategories";
import { useSpendingByCategory } from "../../hooks/useStats";
import { CATEGORY_COLORS, CHART_COLORS, UNCATEGORIZED_LABEL } from "../../lib/chart-theme";
import { formatCents } from "../../lib/format";
import type { Category, CategorySpending as CategorySpendingBucket } from "../../types";
import { EmptyState } from "../common/EmptyState";
import { ErrorMessage } from "../common/ErrorMessage";
import { LoadingSpinner } from "../common/LoadingSpinner";
import { Card } from "../ui/Card";
import { SectionHeader } from "../ui/SectionHeader";

const BAR_HEIGHT_PX = 32;
const CHART_PADDING_PX = 24;

interface ChartRow {
  label: string;
  color: string;
  total_cents: number;
}

/**
 * Ranked bars rather than a pie: with 14 categories plus the uncategorised
 * bucket, pie slices are too small to label or compare (ARCH-024 KD 5).
 */
function toChartRows(buckets: CategorySpendingBucket[], categories: Category[]): ChartRow[] {
  const labelByKey = new Map(categories.map((category) => [category.key, category.label]));

  return buckets.map((bucket) => ({
    label: bucket.category_key
      ? (labelByKey.get(bucket.category_key) ?? bucket.category_key)
      : UNCATEGORIZED_LABEL,
    color: CATEGORY_COLORS[bucket.category_key ?? "uncategorized"],
    total_cents: bucket.total_cents,
  }));
}

export function CategorySpending() {
  const spending = useSpendingByCategory();
  const categories = useCategories();

  const rows =
    spending.data && categories.data ? toChartRows(spending.data, categories.data) : undefined;

  return (
    <Card>
      <SectionHeader title="Ausgaben nach Kategorie" />

      {(spending.isLoading || categories.isLoading) && <LoadingSpinner />}
      {spending.isError && (
        <ErrorMessage
          message="Ausgaben nach Kategorie konnten nicht geladen werden."
          onRetry={spending.refetch}
        />
      )}
      {rows && rows.length === 0 && <EmptyState message="Noch keine Ausgabendaten vorhanden." />}
      {rows && rows.length > 0 && (
        <div
          data-testid="category-chart"
          style={{ width: "100%", height: rows.length * BAR_HEIGHT_PX + CHART_PADDING_PX }}
        >
          <ResponsiveContainer>
            <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 16 }}>
              <XAxis
                type="number"
                tickFormatter={(value: number) => formatCents(value)}
                stroke={CHART_COLORS.axis}
                tickLine={false}
                axisLine={false}
                fontSize={12}
              />
              <YAxis
                type="category"
                dataKey="label"
                stroke={CHART_COLORS.axis}
                tickLine={false}
                axisLine={false}
                fontSize={12}
                width={110}
              />
              <Tooltip formatter={(value: number) => formatCents(value)} />
              <Bar dataKey="total_cents" radius={[0, 4, 4, 0]}>
                {rows.map((row) => (
                  <Cell key={row.label} fill={row.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {rows && rows.length > 0 && (
        <ul className="mt-4 divide-y divide-surface-border">
          {rows.map((row) => (
            <li key={row.label} className="flex items-center gap-3 py-2 text-sm">
              <span
                aria-hidden="true"
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: row.color }}
              />
              <span className="truncate text-gray-900">{row.label}</span>
              <span className="ml-auto font-medium tabular-nums text-gray-900">
                {formatCents(row.total_cents)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
