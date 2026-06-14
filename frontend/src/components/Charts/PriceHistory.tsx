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
import { formatCents, rangeToFromDate } from "../../lib/format";
import type { PriceHistoryRange } from "../../types";
import { EmptyState } from "../common/EmptyState";
import { ErrorMessage } from "../common/ErrorMessage";
import { LoadingSpinner } from "../common/LoadingSpinner";

const RANGES: PriceHistoryRange[] = ["3m", "6m", "12m", "all"];

export function PriceHistory() {
  const products = useProducts();
  const selectedProductId = useUiStore((state) => state.selectedProductId);
  const setSelectedProductId = useUiStore((state) => state.setSelectedProductId);
  const range = useUiStore((state) => state.priceHistoryRange);
  const setRange = useUiStore((state) => state.setPriceHistoryRange);

  const fromDate = rangeToFromDate(range);
  const priceTrend = usePriceTrend(selectedProductId, fromDate);

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">Price history</h2>
        <div className="flex items-center gap-2">
          <select
            aria-label="Select product"
            value={selectedProductId ?? ""}
            onChange={(event) =>
              setSelectedProductId(event.target.value ? Number(event.target.value) : null)
            }
            className="rounded border border-gray-300 px-2 py-1 text-sm"
          >
            <option value="">Select a product</option>
            {products.data?.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name}
              </option>
            ))}
          </select>
          <div role="group" aria-label="Time range" className="flex gap-1">
            {RANGES.map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => setRange(option)}
                aria-pressed={range === option}
                className={`rounded px-2 py-1 text-sm ${
                  range === option ? "bg-gray-800 text-white" : "bg-gray-100 text-gray-700"
                }`}
              >
                {option}
              </button>
            ))}
          </div>
        </div>
      </div>

      {selectedProductId === null && (
        <EmptyState message="Choose a product to view its price history." />
      )}

      {selectedProductId !== null && priceTrend.isLoading && <LoadingSpinner />}
      {selectedProductId !== null && priceTrend.isError && (
        <ErrorMessage message="Failed to load price history." onRetry={priceTrend.refetch} />
      )}
      {priceTrend.data && priceTrend.data.points.length === 0 && (
        <EmptyState message="No price history available for this product." />
      )}
      {priceTrend.data && priceTrend.data.points.length > 0 && (
        <>
          <div className="mb-2 flex gap-4 text-sm text-gray-600">
            <span>Min: {formatCents(priceTrend.data.min_price_cents)}</span>
            <span>Max: {formatCents(priceTrend.data.max_price_cents)}</span>
            <span>Avg: {formatCents(priceTrend.data.avg_price_cents)}</span>
          </div>
          <div data-testid="price-history-chart" style={{ width: "100%", height: 250 }}>
            <ResponsiveContainer>
              <LineChart data={priceTrend.data.points}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis tickFormatter={(value: number) => formatCents(value)} />
                <Tooltip formatter={(value: number) => formatCents(value)} />
                <Line type="monotone" dataKey="unit_price_cents" stroke="#2563eb" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}
