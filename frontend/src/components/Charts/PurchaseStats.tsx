import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useSpending, useTopItems } from "../../hooks/useStats";
import { useUiStore } from "../../store/useUiStore";
import { CHART_COLORS } from "../../lib/chart-theme";
import { formatCents } from "../../lib/format";
import type { SpendingGranularity } from "../../types";
import { EmptyState } from "../common/EmptyState";
import { ErrorMessage } from "../common/ErrorMessage";
import { LoadingSpinner } from "../common/LoadingSpinner";
import { Card } from "../ui/Card";
import { SectionHeader } from "../ui/SectionHeader";
import { ToggleGroup } from "../ui/ToggleGroup";

const PERIOD_OPTIONS: readonly { value: SpendingGranularity; label: string }[] = [
  { value: "week", label: "Woche" },
  { value: "month", label: "Monat" },
];

export function PurchaseStats() {
  const statsPeriod = useUiStore((state) => state.statsPeriod);
  const setStatsPeriod = useUiStore((state) => state.setStatsPeriod);

  const topItems = useTopItems(10);
  const spending = useSpending(statsPeriod);

  return (
    <div className="space-y-6">
      <Card>
        <SectionHeader
          title="Ausgaben im Zeitverlauf"
          action={
            <ToggleGroup
              label="Zeitraum"
              options={PERIOD_OPTIONS}
              value={statsPeriod}
              onChange={setStatsPeriod}
            />
          }
        />

        {spending.isLoading && <LoadingSpinner />}
        {spending.isError && (
          <ErrorMessage
            message="Ausgabendaten konnten nicht geladen werden."
            onRetry={spending.refetch}
          />
        )}
        {spending.data && spending.data.buckets.length === 0 && (
          <EmptyState message="Noch keine Ausgabendaten vorhanden." />
        )}
        {spending.data && spending.data.buckets.length > 0 && (
          <div data-testid="spending-chart" style={{ width: "100%", height: 260 }}>
            <ResponsiveContainer>
              <BarChart data={spending.data.buckets}>
                <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
                <XAxis dataKey="period" stroke={CHART_COLORS.axis} tickLine={false} fontSize={12} />
                <YAxis
                  tickFormatter={(value: number) => formatCents(value)}
                  stroke={CHART_COLORS.axis}
                  tickLine={false}
                  axisLine={false}
                  fontSize={12}
                  width={80}
                />
                <Tooltip formatter={(value: number) => formatCents(value)} />
                <Bar dataKey="total_cents" fill={CHART_COLORS.series} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      <Card>
        <SectionHeader title="Meistgekaufte Artikel" />
        {topItems.isLoading && <LoadingSpinner />}
        {topItems.isError && (
          <ErrorMessage
            message="Meistgekaufte Artikel konnten nicht geladen werden."
            onRetry={topItems.refetch}
          />
        )}
        {topItems.data && topItems.data.length === 0 && (
          <EmptyState message="Noch keine Einkäufe erfasst." />
        )}
        {topItems.data && topItems.data.length > 0 && (
          <ul data-testid="top-items-list" className="divide-y divide-surface-border">
            {topItems.data.map((item, index) => (
              <li
                key={item.product_id}
                className="grid grid-cols-[1.5rem_1fr_auto_auto] items-center gap-3 py-2.5 text-sm"
              >
                <span className="tabular-nums text-gray-400">{index + 1}</span>
                <span className="truncate text-gray-900">{item.product_name}</span>
                <span className="tabular-nums text-gray-500">{item.total_quantity}×</span>
                <span className="w-24 text-right font-medium tabular-nums text-gray-900">
                  {formatCents(item.total_spend_cents)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
