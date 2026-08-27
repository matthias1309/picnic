import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useProducts } from "../../hooks/useProducts";
import { usePriceTrend } from "../../hooks/useStats";
import { useUiStore } from "../../store/useUiStore";
import { CHART_COLORS } from "../../lib/chart-theme";
import { formatCents, rangeToFromDate } from "../../lib/format";
import type { PriceHistoryRange } from "../../types";
import { EmptyState } from "../common/EmptyState";
import { ErrorMessage } from "../common/ErrorMessage";
import { LoadingSpinner } from "../common/LoadingSpinner";
import { Card } from "../ui/Card";
import { SectionHeader } from "../ui/SectionHeader";
import { ToggleGroup } from "../ui/ToggleGroup";
import { ProductCombobox } from "./ProductCombobox";

const RANGE_OPTIONS: readonly { value: PriceHistoryRange; label: string }[] = [
  { value: "3m", label: "3 Mon." },
  { value: "6m", label: "6 Mon." },
  { value: "12m", label: "12 Mon." },
  { value: "all", label: "Gesamt" },
];

export function PriceHistory() {
  const products = useProducts();
  const selectedProductId = useUiStore((state) => state.selectedProductId);
  const setSelectedProductId = useUiStore((state) => state.setSelectedProductId);
  const range = useUiStore((state) => state.priceHistoryRange);
  const setRange = useUiStore((state) => state.setPriceHistoryRange);

  const fromDate = rangeToFromDate(range);
  const priceTrend = usePriceTrend(selectedProductId, fromDate);

  return (
    <Card>
      <SectionHeader
        title="Preisverlauf"
        action={
          <div className="flex flex-wrap items-center gap-2">
            <ProductCombobox
              products={products.data ?? []}
              selectedProductId={selectedProductId}
              onSelect={setSelectedProductId}
            />
            <ToggleGroup
              label="Zeitraum"
              options={RANGE_OPTIONS}
              value={range}
              onChange={setRange}
            />
          </div>
        }
      />

      {selectedProductId === null && (
        <EmptyState message="Wähle einen Artikel, um seinen Preisverlauf zu sehen." />
      )}

      {selectedProductId !== null && priceTrend.isLoading && <LoadingSpinner />}
      {selectedProductId !== null && priceTrend.isError && (
        <ErrorMessage
          message="Preisverlauf konnte nicht geladen werden."
          onRetry={priceTrend.refetch}
        />
      )}
      {priceTrend.data && priceTrend.data.points.length === 0 && (
        <EmptyState message="Für diesen Artikel liegt kein Preisverlauf vor." />
      )}
      {priceTrend.data && priceTrend.data.points.length > 0 && (
        <>
          <div className="mb-4 flex flex-wrap gap-2 text-sm">
            <span className="rounded-lg bg-surface-muted px-3 py-1 tabular-nums text-gray-700">
              Min. {formatCents(priceTrend.data.min_price_cents)}
            </span>
            <span className="rounded-lg bg-surface-muted px-3 py-1 tabular-nums text-gray-700">
              Max. {formatCents(priceTrend.data.max_price_cents)}
            </span>
            <span className="rounded-lg bg-surface-muted px-3 py-1 tabular-nums text-gray-700">
              Ø {formatCents(priceTrend.data.avg_price_cents)}
            </span>
          </div>
          <div data-testid="price-history-chart" style={{ width: "100%", height: 260 }}>
            <ResponsiveContainer>
              <LineChart data={priceTrend.data.points}>
                <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
                <XAxis dataKey="date" stroke={CHART_COLORS.axis} tickLine={false} fontSize={12} />
                <YAxis
                  tickFormatter={(value: number) => formatCents(value)}
                  stroke={CHART_COLORS.axis}
                  tickLine={false}
                  axisLine={false}
                  fontSize={12}
                  width={80}
                />
                <Tooltip formatter={(value: number) => formatCents(value)} />
                <Line
                  type="monotone"
                  dataKey="unit_price_cents"
                  stroke={CHART_COLORS.series}
                  strokeWidth={2}
                  dot={{ r: 3, fill: CHART_COLORS.series }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </Card>
  );
}
