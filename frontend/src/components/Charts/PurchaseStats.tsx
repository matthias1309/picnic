import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useSpending, useTopItems } from "../../hooks/useStats";
import { useUiStore } from "../../store/useUiStore";
import { formatCents } from "../../lib/format";
import { EmptyState } from "../common/EmptyState";
import { ErrorMessage } from "../common/ErrorMessage";
import { LoadingSpinner } from "../common/LoadingSpinner";

const PERIODS = ["week", "month"] as const;

export function PurchaseStats() {
  const statsPeriod = useUiStore((state) => state.statsPeriod);
  const setStatsPeriod = useUiStore((state) => state.setStatsPeriod);

  const topItems = useTopItems(10);
  const spending = useSpending(statsPeriod);

  return (
    <div className="space-y-6">
      <div>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Spending over time</h2>
          <div role="group" aria-label="Aggregation period" className="flex gap-2">
            {PERIODS.map((period) => (
              <button
                key={period}
                type="button"
                onClick={() => setStatsPeriod(period)}
                aria-pressed={statsPeriod === period}
                className={`rounded px-3 py-1 text-sm ${
                  statsPeriod === period ? "bg-gray-800 text-white" : "bg-gray-100 text-gray-700"
                }`}
              >
                {period === "week" ? "Week" : "Month"}
              </button>
            ))}
          </div>
        </div>

        {spending.isLoading && <LoadingSpinner />}
        {spending.isError && (
          <ErrorMessage message="Failed to load spending data." onRetry={spending.refetch} />
        )}
        {spending.data && spending.data.buckets.length === 0 && (
          <EmptyState message="No spending data available yet." />
        )}
        {spending.data && spending.data.buckets.length > 0 && (
          <div data-testid="spending-chart" style={{ width: "100%", height: 250 }}>
            <ResponsiveContainer>
              <BarChart data={spending.data.buckets}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" />
                <YAxis tickFormatter={(value: number) => formatCents(value)} />
                <Tooltip formatter={(value: number) => formatCents(value)} />
                <Bar dataKey="total_cents" fill="#2563eb" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div>
        <h2 className="mb-2 text-lg font-semibold">Top purchased items</h2>
        {topItems.isLoading && <LoadingSpinner />}
        {topItems.isError && (
          <ErrorMessage message="Failed to load top items." onRetry={topItems.refetch} />
        )}
        {topItems.data && topItems.data.length === 0 && (
          <EmptyState message="No purchases recorded yet." />
        )}
        {topItems.data && topItems.data.length > 0 && (
          <ul data-testid="top-items-list" className="divide-y divide-gray-200">
            {topItems.data.map((item) => (
              <li key={item.product_id} className="flex items-center justify-between py-2">
                <span>{item.product_name}</span>
                <span className="text-gray-500">
                  {item.total_quantity}x · {formatCents(item.total_spend_cents)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
